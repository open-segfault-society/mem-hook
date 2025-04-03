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
    help="Specify the size of the buffer for a specific function in bytes, e.g. malloc 1024 will allocate 1kb for the malloc buffer. Has precedence over --select-buffer-size-writes.",
)
parser.add_argument(
    "-sbsw",
    "--select-buffer-size-writes",
    required=False,
    default=["malloc", "1000", "free", "1000"],
    nargs="+",
    help="Specify the size of the buffer for a specific function in how many writes should \
    be fit before the buffer is full. E.g. 'malloc 10 free 10' will allocate 10 times the size of one allocation-information for the malloc buffer and 10 times the size of one free-information for the free buffer.\
    --select-buffer-size-bytes has precedence over this argument.",
)
parser.add_argument(
    "-pf",
    "--print_frequency",
    default=5,
    help="Specify what inverval in seconds to print the current state of allocations.",
)
parser.add_argument(
    "-rf",
    "--read_frequency",
    default=0,
    help="Specify what inverval in seconds to wait before reading from the profiler.",
)
parser.add_argument(
    "-of",
    "--output_file",
    default=None,
    help="Specify an output file to write to. If the value is None it will print to the terminal.",
)
parser.add_argument(
    "--interactive_graph",
    default="No",
    help="If argument is set to yes it will show an interactive graph showing the current allocation size over time.",
)
args = parser.parse_args()


@dataclass
class BufferSize:
    type: str
    buffer_sizes: list[tuple[str, int]]

    def __str__(self):
        return self.type + str(self.buffer_sizes)


def parse_buffer_size(args) -> BufferSize:
    if args.select_buffer_size_bytes is None:
        buffer_sizes = args.select_buffer_size_writes
        type = "w"
    else:
        buffer_sizes = args.select_buffer_size_bytes
        type = "b"

    if len(buffer_sizes) % 2 != 0:
        print("For each function specify its size in either writes or bytes.")
        exit(1)

    hooks_and_sizes = [
        (buffer_sizes[i], int(buffer_sizes[i + 1]))
        for i in range(0, len(buffer_sizes), 2)
    ]

    buffer = BufferSize(type, hooks_and_sizes)
    return buffer


parse_buffer_size(args)


try:
    hook_functions = args.hook_function
    pid = int(args.pid[0])

    if args.filter_size:
        filter_size = list(map(int, args.filter_size))
    else:
        filter_size = None

    if args.filter_size_range:
        filter_size_range = [tuple(map(int, fsr.split('-'))) for fsr in args.filter_size_range]
    else:
        filter_size_range = []

    print(args)
    print_frequency = args.print_frequency
    outputfile = args.output_file
    print_frequency = args.print_frequency
    read_frequency = args.read_frequency
    log_file = args.output_file
except Exception as e:
    print(f"Error while parsing input arguments: {e}")
    exit(1)
