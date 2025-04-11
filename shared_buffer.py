import mmap
import os
import threading
import time
import cli
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

# Constants
HEAD_SIZE: int = 12
ALLOCATION_SIZE: int = (
    24 + 8 * 20
)  # Accounts for inner padding, currently no padding between allocations
FREE_SIZE: int = 8 + 4 + 4 + 8 * 20


class Type(Enum):
    ALLOCATION = (1,)
    FREE = (2,)


class Allocation:
    def __init__(
        self,
        pointer: int,
        size: int,
        time: float,
        backtrace_size: int,
        backtraces: list[int],
    ):
        self.pointer = pointer
        self.size = size
        self.time = time
        self.backtrace_size = backtrace_size
        self.backtraces = backtraces

    def __str__(self):
        addresses = [hex(value) for value in self.backtraces]
        return f"ALLOCTATION: Address: {hex(self.pointer)}, Size: {self.size}, Time: {self.time}, Backtrace size: {self.backtrace_size}, Backtrace: {addresses}"


class Free:
    def __init__(
        self,
        pointer: int,
        time: float,
        backtrace_size: int,
        backtraces: list[int],
    ):
        self.pointer = pointer
        self.time = time
        self.backtrace_size = backtrace_size
        self.backtraces = backtraces

    def __str__(self):
        addresses = [hex(value) for value in self.backtraces]
        return f"FREE:        Address: {hex(self.pointer)}, Time: {self.time}, Backtrace size: {self.backtrace_size}, Backtrace: {addresses}"


@dataclass
class FunctionStatistics:
    amount: int = 0  # Number of frees/allocation
    sizes: int = 0  # Sizes of the allocations/frees


class Memtracker:
    def __init__(self, log_file: str | None):
        self.log_file = log_file
        self.allocations = {}
        self.total_allocation_size = 0
        self.total_allocations = 0
        self.frees = {}
        self.total_free_size = 0
        self.total_frees = 0
        self.all_allocations = {}

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

    def add_allocation(self, allocation: Allocation):
        # TODO: nullptr? Could they be some edge case?
        self.allocations[allocation.pointer] = allocation
        self.all_allocations[allocation.pointer] = allocation
        self.total_allocation_size += allocation.size
        self.total_allocations += 1

        # Update some statistics
        for address in allocation.backtraces:

            self.current_function_allocations[address].sizes += allocation.size
            self.current_function_allocations[address].amount += 1

            self.total_function_allocations[address].sizes += allocation.size
            self.total_function_allocations[address].amount += 1

    def add_free(self, free: Free):
        # TODO: Do we care about saving what pointers we've freed? They can and most likely will be reused
        self.frees[free.pointer] = free

        try:
            size = self.allocations[free.pointer].size
            self.total_free_size += size
        except KeyError:
            size = 0
        self.total_frees += 1

        # Update some statistics
        for address in free.backtraces:

            self.current_function_frees[address].sizes += size
            self.current_function_frees[address].amount += 1

            self.total_function_frees[address].sizes += size
            self.total_function_frees[address].amount += 1

    def remove_allocation(self, pointer: int):
        # TODO: Do we want to remove any freed memory?
        # Could there be value in seeing the total allocations along side
        # the current ones?
        try:
            allocation = self.allocations[pointer]
        except KeyError:
            # Allocation was probably made before hook got injected
            # or we missed it
            return

        self.total_allocation_size -= allocation.size
        self.total_allocations -= 1

        # Remove allocation from each function in backtrace
        for address in allocation.backtraces:
            self.current_function_allocations[address].sizes -= allocation.size
            self.current_function_allocations[address].amount -= 1

        del self.allocations[pointer]

    def log_every_event(self, file):

        self.print_header("Every event", file)

        all_event = list(self.frees.values()) + list(self.all_allocations.values())
        all_event = sorted(all_event, key=lambda x: x.time)

        for event in all_event:

            if isinstance(event, Allocation):
                print(f"Allocation of size {event.size} at time: {event.time}.", file=file)
                print(f"Backtrace:", file=file)
                backtrace_str = ""
                for backtrace in event.backtraces:
                    backtrace_str += str(hex(backtrace)) + " "
                backtrace_str += "\n"
                print(backtrace_str, file=file)

            if isinstance(event, Free):
                try:
                    size = self.allocations[event.pointer].size
                    self.total_free_size += size
                    print(f"Free of size {size} at time: {event.time}.", file=file)
                except KeyError:
                    print(f"Free of size unknown at time: {event.time}.", file=file)

                print(f"Backtrace:", file=file)
                backtrace_str = ""
                for backtrace in event.backtraces:
                    backtrace_str += str(hex(backtrace)) + " "
                backtrace_str += "\n"
                print(backtrace_str, file=file)


    def write_log_file(self):
        if not self.log_file:
            return

        with open(self.log_file, "a") as f:
            self.log_every_event(f)
            self.print_statistics(10, f)

    def print_size(
        self,
        addresses: list[int],
        function_statistics: dict[int, FunctionStatistics],
        type: Type,
        file=None,
    ):
        for key in addresses:
            print(
                f"Address: {hex(key)} - "
                + type.name
                + f": {function_statistics[key].sizes }",
                file=file,
            )

    def print_num(
        self,
        addresses: list[int],
        function_statistics: dict[int, FunctionStatistics],
        type: Type,
        file=None,
    ):
        for key in addresses:
            print(
                f"Address: {hex(key)} - "
                + type.name
                + f" size: {function_statistics[key].amount}",
                file=file,
            )

    def print_header(self, header: str, file=None):
        width = 20
        print("=" * width, file=file)
        print(header.center(width), file=file)
        print("=" * width, file=file)

    def print_statistics(self, delay: int, file=None):
        threading.Timer(delay, self.print_statistics, [delay]).start()
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
        if (self.malloc_overflow):
            print("MALLOC BUFFER OVERFLOW!")
        if (self.free_overflow):
            print("FREE BUFFER OVERFLOW!")
        self.print_header("Current allocation information")
        print("Functions with most number allocations:")
        self.print_size(
            current_most_allocations,
            self.current_function_allocations,
            Type.ALLOCATION,
            file,
        )

        print("Functions with largest total allocation size:", file=file)
        self.print_num(
            current_largest_allocations,
            self.current_function_allocations,
            Type.ALLOCATION,
            file,
        )

        self.print_header("Total allocation information")
        print("Functions with most number allocations:")
        self.print_size(
            total_most_allocations,
            self.total_function_allocations,
            Type.ALLOCATION,
            file,
        )

        print("Functions with largest total allocation size:", file=file)
        self.print_num(
            total_largest_allocations,
            self.total_function_allocations,
            Type.ALLOCATION,
            file,
        )

        self.print_header("Total free information", file)
        print("Functions with most number frees:", file=file)
        self.print_size(total_most_frees, self.total_function_frees, Type.FREE, file)

        print("Functions with largest total free size:")
        self.print_num(total_largest_frees, self.total_function_frees, Type.FREE)
        print()


class SharedBuffer:
    MALLOC_MOUNT: str = "/dev/shm/mem_hook_alloc"
    FREE_MOUNT: str = "/dev/shm/mem_hook_free"
    size: int

    def __init__(self, timestamp: str | None):
        self.timestamp = timestamp

    def __enter__(self):
        # Open the shared memory object
        try:
            # Open the shared memory object (O_RDWR for read-write access)
            self.malloc_fd = os.open(self.MALLOC_MOUNT, os.O_RDWR)
            self.free_fd = os.open(self.FREE_MOUNT, os.O_RDWR)
        except OSError as e:
            print(f"Failed to open shared memory: {e}")
            exit(1)

        # Get the size of the shared memory object by using fstat
        self.malloc_size = os.fstat(self.malloc_fd).st_size
        self.free_size = os.fstat(self.free_fd).st_size

        self.malloc_entries = self.malloc_size // ALLOCATION_SIZE
        self.free_entries = self.free_size // FREE_SIZE

        self.take_time = False
        if not self.timestamp:
            self.take_time = True

        # Map the shared memory object to the Python process's memory space
        try:
            self.malloc_mem = mmap.mmap(
                self.malloc_fd, self.malloc_size, access=mmap.ACCESS_WRITE
            )
            self.free_mem = mmap.mmap(
                self.free_fd, self.free_size, access=mmap.ACCESS_WRITE
            )
        except Exception as e:
            print(f"Failed to map shared memory: {e}")
            os.close(self.malloc_fd)
            os.close(self.free_fd)
            exit(1)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.malloc_fd is None or self.malloc_mem is None:
            return
        if self.free_fd is None or self.free_mem is None:
            return

        self.malloc_mem.close()
        os.close(self.malloc_fd)
        self.free_mem.close()
        os.close(self.free_fd)

    def read_backtraces(self, start_address, backtrace_size, malloc=True) -> list[int]:
        if backtrace_size == 0:
            return []

        backtraces = []
        read_pointers = 0

        if malloc:
            mem = self.malloc_mem
        else:
            mem = self.free_mem

        while read_pointers != backtrace_size:
            backtraces.append(
                int.from_bytes(
                    mem[
                        start_address
                        + read_pointers * 8 : start_address
                        + (read_pointers + 1) * 8
                    ],
                    byteorder="little",
                )
            )
            read_pointers += 1

        return backtraces

    def read_allocation(self, head: int) -> Allocation:
        start_address = head * ALLOCATION_SIZE + HEAD_SIZE
        pointer = int.from_bytes(
            self.malloc_mem[start_address : start_address + 8], byteorder="little"
        )
        size = int.from_bytes(
            self.malloc_mem[start_address + 8 : start_address + 12], byteorder="little"
        )
        if self.take_time:
            current_time = time.time()
        else:
            current_time = int.from_bytes(
                self.malloc_mem[start_address + 8 : start_address + 12], byteorder="little"
            )
        current_time = time.time()
        backtrace_size = int.from_bytes(
            self.malloc_mem[start_address + 16 : start_address + 20], byteorder="little"
        )

        backtraces = self.read_backtraces(start_address + 24, backtrace_size)

        return Allocation(pointer, size, current_time, backtrace_size, backtraces)

    def read_free(self, head: int) -> Free:
        # assumes 8 bytes pointers aka 64-bit system
        start_address = head * FREE_SIZE + HEAD_SIZE
        pointer = int.from_bytes(
            self.free_mem[start_address : start_address + 8], byteorder="little"
        )
        if self.take_time:
            current_time = time.time()
        else:
            current_time = int.from_bytes(
                self.malloc_mem[start_address + 8 : start_address + 12], byteorder="little"
            )
        backtrace_size = int.from_bytes(
            self.free_mem[start_address + 12 : start_address + 16], byteorder="little"
        )

        backtraces = self.read_backtraces(
            start_address + 16, backtrace_size, malloc=False
        )

        return Free(pointer, current_time, backtrace_size, backtraces)

    def read(self, memtracker: Memtracker):
        malloc_head = int.from_bytes(self.malloc_mem[0:4], byteorder="little")
        malloc_tail = int.from_bytes(self.malloc_mem[4:8], byteorder="little")
        memtracker.malloc_overflow = int.from_bytes(self.malloc_mem[8:12], byteorder="little")

        free_head = int.from_bytes(self.free_mem[0:4], byteorder="little")
        free_tail = int.from_bytes(self.free_mem[4:8], byteorder="little")
        memtracker.free_overflow = int.from_bytes(self.free_mem[8:12], byteorder="little")

        # =================
        #       MALLOC
        # =================

        while malloc_head != malloc_tail:
            allocation = self.read_allocation(malloc_head)
            memtracker.add_allocation(allocation)
            malloc_head = (malloc_head + 1) % self.malloc_entries

        self.malloc_mem[0:4] = malloc_head.to_bytes(4, byteorder="little")

        # =================
        #       FREE
        # =================

        while free_head != free_tail:
            free = self.read_free(free_head)
            # add_free must be called before remove_allocation
            # since we use info from allocation to get free size
            memtracker.add_free(free)
            memtracker.remove_allocation(free.pointer)
            free_head = (free_head + 1) % self.free_entries

        self.free_mem[0:4] = free_head.to_bytes(4, byteorder="little")
