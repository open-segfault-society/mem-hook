import mmap
import os
import random
from threading import Timer
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
from functools import partial

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import cli

# Constants
HEAD_SIZE: int = 12
TRACE_SIZE: int = (
    32 + 8 * 20
)  # Accounts for inner padding, currently no padding between allocations


class TraceType(IntEnum):
    MALLOC = 0
    NEW = 1
    NEW_ARRAY = 2
    NEW_NO_THROW = 3
    FREE = 4
    DELETE = 5
    DELETE_ARRAY = 6
    DELETE_NO_THROW = 7


class GraphType(IntEnum):
    ALLOCATION = 0
    DEALLOCATION = 1


class Trace:
    def __init__(
        self,
        address: int,
        time: float,
        size: int,
        backtrace_size: int,
        type: TraceType,
        backtraces: list[int],
    ):
        self.address = address
        self.size = size
        self.time = time
        self.backtrace_size = backtrace_size
        self.type = type
        self.backtraces = backtraces

    def __str__(self):
        addresses = [hex(value) for value in self.backtraces]
        return f"ALLOCTATION: Address: {hex(self.address)}, Size: {self.size}, Time: {self.time}, Backtrace size: {self.backtrace_size}, Backtrace: {addresses}"


class Graph:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600

    def __init__(self, time_window: int):
        self.time_window = time_window
        matplotlib.use("TkAgg")  # Use backend that supports scrolling
        self.x_data, self.y_data = [], []
        self.allocs: list[tuple[float, int]] = []
        self.frees: list[tuple[float, int]] = []

        self.fig, self.ax = plt.subplots(
            figsize=(self.WINDOW_WIDTH / 100, self.WINDOW_HEIGHT / 100), dpi=100
        )
        (self.line,) = self.ax.plot([], [])
        self.alloc_scatter = self.ax.scatter(
            [], [], marker="^", color="g", label="alloc", s=25
        )
        self.free_scatter = self.ax.scatter(
            [], [], marker="v", color="r", label="free", s=25
        )
        self.alloc_scatter.set_zorder(999)
        self.free_scatter.set_zorder(999)
        self.mem_label = self.fig.text(0.15, 0.90, "", fontsize=12)

        self.redraw = True
        self.autoscroll = False

        self.ax.set_navigate(True)  # Enable panning and zooming
        self.ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._size_format))
        plt.ion()  # Set interactive mode
        plt.legend()
        plt.show(block=False)

    def update(self):
        # Scroll the x-axis dynamically
        min_x = 0
        max_x = 0

        if len(self.x_data) > 1:
            min_x = min(self.x_data)
            max_x = max(self.x_data)

        if self.redraw:
            self.line.set_data(self.x_data, self.y_data)
            self.ax.relim()
            self.ax.autoscale_view()

            if self.allocs:
                self.alloc_scatter.set_offsets(self.allocs)
            if self.frees:
                self.free_scatter.set_offsets(self.frees)

            if self.autoscroll:
                self.ax.set_xlim(max(min_x, max_x - self.time_window), max_x)

            if self.y_data:
                self.mem_label.set_text(f"Memory: {self._get_size(self.y_data[-1])}")

            self.fig.canvas.draw()  # Redraw figure
            self.redraw = False

        self.autoscroll = max_x <= self.ax.get_xlim()[1]
        self.fig.canvas.flush_events()  # Process GUI events

    def add_event(self, time: float, size: int, operation: GraphType):
        self.x_data.append(time)
        self.y_data.append(size)

        match operation:
            case GraphType.ALLOCATION:
                self.allocs.append((time, size))
            case GraphType.DEALLOCATION:
                self.frees.append((time, size))

        self.redraw = True

    def _size_format(self, x, pos):
        return self._get_size(x)

    def _get_size(self, num):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num < 1024.0:
                return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} PB"


@dataclass
class FunctionStatistics:
    amount: int = 0  # Number of frees/allocation
    sizes: int = 0  # Sizes of the allocations/frees


# Memtracker does not distingish between the different types of allocations/frees
# e.g. it will treat malloc/new/new[] as simply an allocation. Same for free/delete/delete[]
# The information will still be available
class Memtracker:
    def __init__(self, log_file: str | None):
        self.log_file = log_file
        self.allocations = {}
        self.total_allocation_size: int = 0
        self.total_allocations = 0
        self.frees = {}
        self.total_free_size = 0
        self.total_frees = 0
        self.time_start = time.time()
        self.all_allocations: list[Trace] = []
        self.all_frees: list[Trace] = []

        self.print_timer: Timer | None = None

        self.malloc_overflow = 0
        self.free_overflow = 0

        # Saves the number and sizes of allocation per function (address)
        # from its backtrace
        # Key is address, value is list containing the total size and total allocations
        self.current_function_allocations: dict[int, FunctionStatistics] = defaultdict(
            lambda: FunctionStatistics()
        )
        self.total_function_allocations: dict[int, FunctionStatistics] = defaultdict(
            lambda: FunctionStatistics()
        )
        self.current_function_frees: dict[int, FunctionStatistics] = defaultdict(
            lambda: FunctionStatistics()
        )
        self.total_function_frees: dict[int, FunctionStatistics] = defaultdict(
            lambda: FunctionStatistics()
        )

        self.graph: Graph | None = None

    def do_event_loop(self):
        if self.graph is not None:
            self.graph.update()

    def add_allocation(self, trace: Trace):
        self.allocations[trace.address] = trace
        self.all_allocations.append(trace)
        self.total_allocation_size += trace.size
        self.total_allocations += 1

        if self.graph is not None:
            alloc_time = round(trace.time - self.time_start, 2)
            self.graph.add_event(
                alloc_time, self.total_allocation_size, GraphType.ALLOCATION
            )
            self.graph.update()

        # Update some statistics
        for address in trace.backtraces:

            self.current_function_allocations[address].sizes += trace.size
            self.current_function_allocations[address].amount += 1

            self.total_function_allocations[address].sizes += trace.size
            self.total_function_allocations[address].amount += 1

    def add_trace(self, trace: Trace):
        # TODO: nullptr? Could they be some edge case?
        if trace.type in [
            TraceType.MALLOC,
            TraceType.NEW,
            TraceType.NEW_ARRAY,
            TraceType.NEW_NO_THROW,
        ]:
            self.add_allocation(trace)
        else:
            self.add_deallocation(trace)

    def add_deallocation(self, trace: Trace):
        # TODO: Do we care about saving what pointers we've freed? They can and most likely will be reused
        try:
            original_trace = self.allocations[trace.address]
            trace.size = original_trace.size
            del self.allocations[trace.address]
            self.total_free_size += trace.size
            self.total_allocation_size -= trace.size
        except KeyError:
            original_trace = None
            trace.size = 0
        self.total_frees += 1

        self.frees[trace.address] = trace
        self.all_frees.append(trace)

        if self.graph is not None:
            free_time = round(trace.time - self.time_start, 2)
            self.graph.add_event(
                free_time, self.total_allocation_size, GraphType.DEALLOCATION
            )
            self.graph.update()

        # Update some statistics
        for address in trace.backtraces:
            self.current_function_frees[address].sizes += trace.size
            self.current_function_frees[address].amount += 1

            self.total_function_frees[address].sizes += trace.size
            self.total_function_frees[address].amount += 1

        if original_trace:
            for address in original_trace.backtraces:
                self.current_function_allocations[address].sizes -= trace.size
                self.current_function_allocations[address].amount -= 1

    def log_every_event(self, file) -> int:
        self.print_header("Every event", file)

        all_events: list[Trace] = self.all_frees + self.all_allocations
        all_events = sorted(all_events, key=lambda x: x.time)

        for event in all_events:
            print(
                f"[{event.type.name}] size={event.size if event.size else '?'} at t={event.time}",
                file=file,
            )
            print(
                f"    Backtrace: {' -> '.join(str(hex(b)) for b in event.backtraces)}\n",
                file=file,
            )
        return len(all_events)

    def write_log_file(self):
        if not self.log_file:
            return

        with open(self.log_file, "a") as f:
            event_count = self.log_every_event(f)
            self.print_statistics(0, file=f, loop=False)

        print(f"All statistics have been written to '{self.log_file}'. Total records: {event_count}")

    def print_size(
        self,
        addresses: list[int],
        function_statistics: dict[int, FunctionStatistics],
        file=None,
    ):
        for key in addresses:
            entry = function_statistics[key]
            print(
                f"  - {hex(key):<16} - {entry.sizes} bytes ({entry.amount} calls)",
                file=file,
            )

    def print_num(
        self,
        addresses: list[int],
        function_statistics: dict[int, FunctionStatistics],
        file=None,
    ):
        for key in addresses:
            entry = function_statistics[key]
            print(
                f"  - {hex(key):<16} - {entry.amount} calls ({entry.sizes} bytes)",
                file=file,
            )

    def print_header(self, header: str, file=None):
        width = 32
        print("=" * width, file=file)
        print(header.center(width), file=file)
        print("=" * width + "\n", file=file)

    def print_statistics_stop(self):
        if self.print_timer:
            self.print_timer.cancel()

    def print_statistics(self, delay: int, file=None, loop=True):
        if loop:
            self.print_timer = Timer(delay, self.print_statistics, [delay])
            self.print_timer.start()

        current_most_allocations = sorted(
            self.current_function_allocations.keys(),
            key=lambda k: self.current_function_allocations[k].amount,
            reverse=True,
        )
        current_largest_allocations = sorted(
            self.current_function_allocations.keys(),
            key=lambda k: self.current_function_allocations[k].sizes,
            reverse=True,
        )
        total_most_allocations = sorted(
            self.total_function_allocations.keys(),
            key=lambda k: self.total_function_allocations[k].amount,
            reverse=True,
        )
        total_largest_allocations = sorted(
            self.total_function_allocations.keys(),
            key=lambda k: self.total_function_allocations[k].sizes,
            reverse=True,
        )
        total_most_frees = sorted(
            self.total_function_frees.keys(),
            key=lambda k: self.total_function_frees[k].amount,
            reverse=True,
        )
        total_largest_frees = sorted(
            self.total_function_frees.keys(),
            key=lambda k: self.total_function_frees[k].sizes,
            reverse=True,
        )

        # Skip printing if there is no data
        if not total_most_allocations and not total_most_frees:
            return

        if self.malloc_overflow:
            print("MALLOC BUFFER OVERFLOW!")
        if self.free_overflow:
            print("FREE BUFFER OVERFLOW!")

        self.print_header("Current Allocation Summary", file)

        print("Top Allocation Functions by Total Calls:", file=file)
        self.print_num(
            current_most_allocations,
            self.current_function_allocations,
            file,
        )
        print(file=file)

        print("Top Allocation Functions by Total Size:", file=file)
        self.print_size(
            current_largest_allocations,
            self.current_function_allocations,
            file,
        )
        print(file=file)

        self.print_header("Total Allocation Summary", file=file)

        print("Top Allocation Functions by Total Calls:", file=file)
        self.print_num(
            total_most_allocations,
            self.total_function_allocations,
            file,
        )
        print(file=file)

        print("Top Allocation Functions by Total Size:", file=file)
        self.print_size(
            total_largest_allocations,
            self.total_function_allocations,
            file,
        )
        print(file=file)

        self.print_header("Total Free Summary", file)
        print("Top Free Functions by Total Calls:", file=file)
        self.print_num(total_most_frees, self.total_function_frees, file)
        print(file=file)

        print("Top Free Functions by Total Size:", file=file)
        self.print_size(total_largest_frees, self.total_function_frees, file)
        print(file=file)

    def display_graph(self, time_window: int):
        self.graph = Graph(time_window)


class SharedBuffer:
    MOUNT: str = "/dev/shm/mem_hook"
    size: int

    def __init__(self, timestamp: str | None):
        self.timestamp = timestamp

    def __enter__(self):
        # Open the shared memory object
        try:
            # Open the shared memory object (O_RDWR for read-write access)
            self.fd = os.open(self.MOUNT, os.O_RDWR)
        except OSError as e:
            print(f"Failed to open shared memory: {e}")
            exit(1)

        # Get the size of the shared memory object by using fstat
        self.size = os.fstat(self.fd).st_size

        self.entries = self.size // TRACE_SIZE

        self.take_time = False
        if not self.timestamp:
            self.take_time = True

        # Map the shared memory object to the Python process's memory space
        try:
            self.mem = mmap.mmap(self.fd, self.size, access=mmap.ACCESS_WRITE)
        except Exception as e:
            print(f"Failed to map shared memory: {e}")
            os.close(self.fd)
            exit(1)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.fd is None or self.mem is None:
            return

        self.mem.close()
        os.close(self.fd)

    def read_backtraces(self, start_address, backtrace_size) -> list[int]:
        if backtrace_size == 0:
            return []

        backtraces = []
        read_pointers = 0

        while read_pointers != backtrace_size:
            backtraces.append(
                int.from_bytes(
                    self.mem[
                        start_address
                        + read_pointers * 8 : start_address
                        + (read_pointers + 1) * 8
                    ],
                    byteorder="little",
                )
            )
            read_pointers += 1

        return backtraces

    def read_trace(self, head: int) -> Trace:
        start_address = head * TRACE_SIZE + HEAD_SIZE
        pointer = int.from_bytes(
            self.mem[start_address : start_address + 8], byteorder="little"
        )
        if self.take_time:
            current_time = time.time()
        else:
            current_time = int.from_bytes(
                self.mem[start_address + 8 : start_address + 16],
                byteorder="little",
            )
        size = int.from_bytes(
            self.mem[start_address + 16 : start_address + 20], byteorder="little"
        )
        backtrace_size = int.from_bytes(
            self.mem[start_address + 20 : start_address + 24], byteorder="little"
        )

        trace_type = int.from_bytes(
            self.mem[start_address + 24 : start_address + 28], byteorder="little"
        )

        type = TraceType(int(trace_type))

        backtraces = self.read_backtraces(start_address + 32, backtrace_size)

        return Trace(pointer, current_time, size, backtrace_size, type, backtraces)

    def read(self, memtracker: Memtracker):
        head = int.from_bytes(self.mem[0:4], byteorder="little")
        tail = int.from_bytes(self.mem[4:8], byteorder="little")
        memtracker.malloc_overflow = int.from_bytes(self.mem[8:12], byteorder="little")

        while head != tail:
            trace = self.read_trace(head)
            memtracker.add_trace(trace)
            head = (head + 1) % self.entries

        self.mem[0:4] = head.to_bytes(4, byteorder="little")

        memtracker.do_event_loop()
