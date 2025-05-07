import argparse
import sys
from dataclasses import dataclass

"""
Goals of the CLI
- Select malloc sizes to filter for (ranges/specific sizes)
- Choose what to hook (free, malloc, calloc, realloc, or any dynamically linked function)
- Choose buffer sizes for the malloc and free buffers
- Python read frequency?
- Output log file
- Live graph, render matplotlib every X sec
- Dash help that explains all above (Stick with GNU/UNIX convention)
"""

parser = argparse.ArgumentParser(
    prog="Memhook",
    description="A memory profiling tool",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "-p",
    "--pid",
    default=None,
    required=True,
    nargs=1,
    help="Specify the process id of the program to profile.",
)
parser.add_argument(
    "-hf",
    "--hook-function",
    default=[
        "malloc",
        "free",
        "_Znwm",
        "_Znam",
        "_ZnwmRKSt9nothrow_t",
        "_ZdlPv",
        "_ZdlPvm",
        "_ZdaPv",
        "_ZdaPvm",
        "_ZdlPvRKSt9nothrow_t",
    ],
    nargs="+",
    help="Specify functions to hook.",
)
parser.add_argument(
    "-fsr",
    "--filter-size-range",
    default=None,
    nargs="+",
    help="Filter allocations to only include those within specified size ranges (e.g., 0-100). You can specify multiple ranges.",
)
parser.add_argument(
    "-fs",
    "--filter-size",
    default=None,
    nargs="+",
    help="Filter allocations to only include specified sizes (e.g., 64 128 256).",
)
parser.add_argument(
    "-sb",
    "--shm-buffer-bytes",
    type=int,
    default=20000000,
    help="Size (in bytes) of the POSIX shared memory region used to transfer data from the hooked process to the profiler.",
)
parser.add_argument(
    "-se",
    "--shm-buffer-entries",
    type=int,
    default=100000,
    help="Maximum number of allocation records the POSIX shared memory region can hold before wrapping."
)
parser.add_argument(
    "-pf",
    "--print-frequency",
    default=5,
    help="Specify print interval (in seconds) of the current state of allocations."
)
parser.add_argument(
    "-rf",
    "--read-frequency",
    default=0,
    help="Specify read interval (in seconds) from the profiler ."
)
parser.add_argument(
    "-o",
    "--output-file",
    default=None,
    help="Write profiler output to a file. If omitted or set to 'None', output will be printed to stdout",
)
parser.add_argument(
    "-g",
    "--graph",
    action="store_true",
    help="Show an interactive graph showing the current allocation size over time.",
)
parser.add_argument(
    "-w",
    "--time-window",
    type=int,
    default=32,
    help="Window of time (in seconds) displayed in the interactive graph."
)
parser.add_argument(
    "--backtrace-method",
    default=["fast"],
    nargs=1,
    choices=["fast", "glibc"],
    help="Choose how to obtain backtraces: 'fast' uses an internal stack walk, 'glibc' uses standard glibc unwinding.",
)
parser.add_argument(
    "-tm",
    "--timestamp-method",
    default=["chrono"],
    nargs=1,
    choices=["chrono", "rdtscp", "None"],
    help="Method used to timestamp allocations. 'chrono' uses high-resolution clock, 'rdtscp' uses CPU instruction.",
)
args = parser.parse_args()


@dataclass
class BufferSize:
    type: str
    size: int

    def __str__(self):
        return self.type + str(self.size)


def verify_filter_sizes(filter_size: list[int]):
    remove_sizes = []

    for size in filter_size:
        if size < 0:
            print(f"Entered size {size} is less then zero and removed")
            remove_sizes.append(size)

    for size in remove_sizes:
        filter_size.remove(size)


# TODO: Fix parsing of buffer from cli
def parse_buffer_size(args) -> BufferSize:
    if "-sb" in sys.argv or "--shm-buffer-bytes" in sys.argv:
        return BufferSize("b", max(256, args.shm_buffer_bytes))
    return BufferSize("w", max(10, args.shm_buffer_entries))

try:
    hook_functions = args.hook_function
    pid = int(args.pid[0])
    buffer_sizes = parse_buffer_size(args)

    if args.filter_size:
        filter_size = list(map(int, args.filter_size))
        verify_filter_sizes(filter_size)
    else:
        filter_size = None

    if args.filter_size_range:
        # Since this cant parse ranges that start with negative values we kinda dont need to verify it
        filter_size_range = [
            tuple(map(int, fsr.split("-"))) for fsr in args.filter_size_range
        ]
    else:
        filter_size_range = []

    print_frequency = args.print_frequency
    outputfile = args.output_file
    print_frequency = args.print_frequency
    read_frequency = args.read_frequency
    backtrace_method = args.backtrace_method[0]
    log_file = args.output_file
    timestamp_method = args.timestamp_method[0]
    graph = args.graph
    time_window = args.time_window

    if print_frequency < 0:
        print(f"Print frequency {print_frequency} is less than zero, changed to 5.")
        print_frequency = 5

    if read_frequency < 0:
        print(f"Read frequency {read_frequency} is less than zero, changed to 0.")
        print_frequency = 0

except Exception as e:
    print(f"Error while parsing input arguments: {e}")
    exit(1)
