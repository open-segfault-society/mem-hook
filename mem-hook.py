import sys
import os
from hook_manager import HookManager

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pid>")
        exit(1)

    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    pid = int(sys.argv[1])
    hook_manager = HookManager(pid)

    # Register hooks-
    hook_manager.register_hook("malloc")
    hook_manager.register_hook("free")

    with hook_manager.inject() as hd:
        try:
            print("\nPress CTRL+C to detach...\n")
            while True:
                pass
        except KeyboardInterrupt:
            pass
