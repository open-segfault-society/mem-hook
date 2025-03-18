import argparse

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
    prog="Memwatch 2.0", description="A memory profiling tool"
)

parser.add_argument(
    "--hook-function",
    default="malloc free",
    help="Specify what functions to hook by providing their names, e.g. '--hook-function malloc free'. defaults to malloc and free",
)
parser.add_argument(
    "--pid",
    default=None,
    required=True,
    help="Specify the process id of the process to profile",
)
parsr.add_argument(
    "--filter-size-range",
    default=None,
    help="Specify what ranges to probe, will ignore all allocations outside the specified range(s). \
    [0-100] would profile all allocations from size 0 to 100 inclusive. Defaults to none.",
)
parser.add_argument(
    "--filter-size",
    default=None,
    help="Specify specific sizes to profile. Defaults to none.",
)
parser.add_argument(
    "--select-buffer-size-bytes",
    default=None,
    help="Specify the size of the buffer for a specific function in bytes, e.g. malloc 1024 will allocate 1kb for the malloc buffer. Has precedence over --select-buffer-size-writes. Defaults to none",
)
parser.add_argument(
    "--select-buffer-size-writes",
    default="malloc 64 free 64",
    help="Specify the size of the buffer for a specific function in how many writes should \
    be fit before the buffer is full. E.g. 'malloc 10 free 10' will allocate 10 times the size of one allocation-information for the malloc buffer and 10 times the size of one free-information for the free buffer.\
    Defaults to 64 for malloc and free unless --select-buffer-size-bytes is specified",
)
parser.add_argument("--read frequency", help="")
parser.add_argument("--output file", help="")
parser.add_argument("--interactive graph", help="")
parser.print_help()
args = parser.parse_args()

hook_functions = [function for function in args.hook_function.split()]
buffer_write_size = args.select_buffer_size_writes.split()
buffer_sizes_in_writes = [
    (buffer_write_size[i], int(buffer_write_size[i + 1]))
    for i in range(0, len(buffer_write_size), 2)
]
pid = args.pid
print(pid)
