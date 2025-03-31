import os
from hook_manager import HookManager
from code_injector import CodeInjector, CodeEntry, CodeEntryFactory
import cli
import shared_buffer


def compile_and_inject():
    code_entries: list[CodeEntry] = []

    if cli.filter_size_range:
        code_entries.append(CodeEntryFactory.malloc_filter_range(cli.filter_size_range))

    if cli.filter_size:
        code_entries.append(CodeEntryFactory.malloc_filter(cli.filter_size))

    CodeInjector.inject(code_entries)


if __name__ == "__main__":
    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    compile_and_inject()

    memtracker = shared_buffer.Memtracker()
    hook_manager = HookManager(cli.pid)

    # Register hooks
    hook_manager.register_hook("malloc")
    hook_manager.register_hook("free")
    # memtracker.print_statistics(cli.print_frequency)
    memtracker.display_graph(1)

    with hook_manager.inject() as hd, shared_buffer.SharedBuffer() as shared_buffer:
        try:
            print("\nPress CTRL+C to detach...\n")
            while True:
                shared_buffer.read(memtracker)
        except KeyboardInterrupt:
            pass
