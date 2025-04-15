import os

import cli
import shared_buffer
from code_injector import CodeEntry, CodeEntryFactory, CodeInjector
from hook_manager import HookManager


def compile_and_inject():
    code_entries: list[CodeEntry] = []

    if cli.filter_size_range:
        code_entries.append(CodeEntryFactory.malloc_filter_range(cli.filter_size_range))

    if cli.filter_size:
        code_entries.append(CodeEntryFactory.malloc_filter(cli.filter_size))

    if cli.backtrace_method == "fast":
        code_entries.append(CodeEntryFactory.backtrace_fast())
    elif cli.backtrace_method == "glibc":
        code_entries.append(CodeEntryFactory.backtrace_glibc())

    code_entries.append(CodeEntryFactory.buffer_sizes(cli.buffer_sizes))

    CodeInjector.inject(code_entries)


if __name__ == "__main__":
    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    compile_and_inject()

    memtracker = shared_buffer.Memtracker(cli.log_file)
    hook_manager = HookManager(cli.pid)

    # Register hooks
    hook_manager.register_hook("malloc")
    hook_manager.register_hook("free")
    hook_manager.register_hook("_Znwm", "new_hook")
    hook_manager.register_hook("_Znam", "array_new_hook")
    hook_manager.register_hook("_ZnwmRKSt9nothrow_t", "non_throw_new_hook")
    hook_manager.register_hook("_ZdlPv", "delete_hook")
    hook_manager.register_hook("_ZdaPv", "array_delete_hook")
    hook_manager.register_hook("_ZdlPvRKSt9nothrow_t", "non_throw_delete_hook")
    # hook_manager.register_hook("_ZnwmPv", "placement_new_hook")
    # hook_manager.register_hook("_ZnaPv", "array_placement_new_hook")

    if cli.graph:
        memtracker.display_graph(cli.time_window)

    if not cli.log_file:
        memtracker.print_statistics(cli.print_frequency)

    with hook_manager.inject() as hd, shared_buffer.SharedBuffer() as shared_buffer:
        try:
            print("\nPress CTRL+C to detach...\n")
            while True:
                shared_buffer.read(memtracker)
        except KeyboardInterrupt:
            memtracker.write_log_file()
