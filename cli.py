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

def verify_sizes(type: str, hooks_and_sizes: list[tuple[str, int]]):

    for i, (hook, size) in enumerate(hooks_and_sizes):
        if type == "w" and size < 1:
            print(f"The size for hook {hook} is less than one write, size changed to 1 write.")
            hooks_and_sizes[i] = (hook, 1)

        if type == "b" and size < 199:
            print(f"The size for hook {hook} is less than 200 bytes, size changed to 200 bytes")
            hooks_and_sizes[i] = (hook, 200)

def verify_filter_sizes(filter_size: list[int]):

    remove_sizes = []

    for size in filter_size:
        if size < 0:
            print(f"Entered size {size} is less then zero and removed")
            remove_sizes.append(size)

    for size in remove_sizes:
        filter_size.remove(size)

def parse_buffer_size(args) -> BufferSize:
    if args.select_buffer_size_bytes is None:
        buffer_sizes = args.select_buffer_size_writes
        type = "w"
    else:
        buffer_sizes = args.select_buffer_size_bytes
        type = "b"

    if len(buffer_sizes) % 2 != 0:
        print("For each function also specify its size.")
        exit(1)

    hooks_and_sizes = [
        (buffer_sizes[i], int(buffer_sizes[i + 1]))
        for i in range(0, len(buffer_sizes), 2)
    ]

    verify_sizes(type, hooks_and_sizes)

    buffer = BufferSize(type, hooks_and_sizes)
    return buffer




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
        filter_size_range = [tuple(map(int, fsr.split('-'))) for fsr in args.filter_size_range]
    else:
        filter_size_range = []

    print_frequency = args.print_frequency
    outputfile = args.output_file
    print_frequency = args.print_frequency
    read_frequency = args.read_frequency
    log_file = args.output_file

    if print_frequency < 0:
        print(f"Print frequency {print_frequency} is less than zero, changed to 5.")
        print_frequency = 5

    if read_frequency < 0:
        print(f"Read frequency {read_frequency} is less than zero, changed to 0.")
        print_frequency = 0

except Exception as e:
    print(f"Error while parsing input arguments: {e}")
    exit(1)
