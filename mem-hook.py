import sys
import os
from hook_manager import HookManager
import cli
import shared_buffer

if __name__ == "__main__":

    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    memtracker = shared_buffer.Memtracker()
    buffer = shared_buffer.SharedBuffer()
    hook_manager = HookManager(cli.pid)

    # Register hooks-
    hook_manager.register_hook("malloc")
    hook_manager.register_hook("free")

    with hook_manager.inject() as hd:
        try:
            print("\nPress CTRL+C to detach...\n")
            while True:
                buffer.read()
        except KeyboardInterrupt:
            pass
