import argparse
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
    prog="Memwatch 2.0",
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
    default="malloc free",
    required=False,
    nargs="+",
    help="Specify what functions to hook by providing their names.",
)
parser.add_argument(
    "-fsr",
    "--filter-size-range",
    default=None,
    required=False,
    nargs="+",
    help="Specify what ranges to probe, will ignore all allocations outside the specified range(s). \
    [0-100] would profile all allocations from size 0 to 100 inclusive.",
)
parser.add_argument(
    "-fs",
    "--filter-size",
    required=False,
    default=None,
    nargs="+",
    help="Specify specific sizes to profile.",
)
parser.add_argument(
    "-sbsb",
    "--select-buffer-size-bytes",
    required=False,
    default=None,
    nargs="+",
    help="Change me",
)
parser.add_argument(
    "-sbsw",
    "--select-buffer-size-writes",
    required=False,
    default=["100000"],
    nargs="+",
    help="Change me",
)
parser.add_argument(
    "-pf",
    "--print-frequency",
    default=5,
    help="Specify what inverval in seconds to print the current state of allocations.",
)
parser.add_argument(
    "-rf",
    "--read-frequency",
    default=0,
    help="Specify what inverval in seconds to wait before reading from the profiler.",
)
parser.add_argument(
    "-of",
    "--output-file",
    default=None,
    help="Specify an output file to write to. If the value is None it will print to the terminal.",
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
)
parser.add_argument(
    "--backtrace-method",
    default=["fast"],
    nargs=1,
    choices=["fast", "glibc"],
    help="The method used for fetching the backtrace",
)
parser.add_argument(
    "-tm",
    "--timestamp-method",
    default=["chrono"],
    nargs=1,
    choices=["chrono", "rdtscp", "None"],
    help="The method used for fetching the backtrace"
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
    if args.select_buffer_size_bytes is None:
        size = int(args.select_buffer_size_writes[0])
        if size < 1:
            size = 1
        type = "w"
    else:
        size = int(args.select_buffer_size_bytes[0])
        if size < 250:
            size = 250
        type = "b"

    return BufferSize(type, size)


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
