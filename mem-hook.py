import os
from hook_manager import HookManager
from code_injector import CodeInjector
import cli
import shared_buffer

if __name__ == "__main__":
    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    rep_map: dict[str, str] = CodeInjector.get_replacement_map()
    CodeInjector.inject(rep_map)

    memtracker = shared_buffer.Memtracker()
    hook_manager = HookManager(cli.pid)

    # Register hooks-
    hook_manager.register_hook("malloc")
    hook_manager.register_hook("free")
    memtracker.print_statistics(cli.print_frequency)


    with hook_manager.inject() as hd, shared_buffer.SharedBuffer() as shared_buffer:
        try:
            print("\nPress CTRL+C to detach...\n")
            while True:
                shared_buffer.read(memtracker)
        except KeyboardInterrupt:
            pass
