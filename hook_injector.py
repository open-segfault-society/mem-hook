import sys
import os
import subprocess
import re

LIB_NAME: str = "hook.so"

def get_lib_path():
    path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(path, LIB_NAME)

LIB_PATH: str = get_lib_path()


def get_process_path(pid: int) -> str:
    output = subprocess.run(["readlink", "-f", f"/proc/{pid}/exe"], capture_output=True, text=True)
    if not output.stdout:
        raise ValueError(f"Could not find the program path for pid {pid}")
    path = output.stdout.strip()
    print(f"Found path for pid {pid}: {path}")
    return path

def get_obj_dump(path: str) -> str:
    output = subprocess.run(["objdump", "-d", path], capture_output=True, text=True)
    return output.stdout.strip()

def get_plt_offset(pid: int, function: str) -> int:
    """Get the offset of the function entry in PLT"""
    p_path = get_process_path(pid)
    obj_dump = get_obj_dump(p_path)
    # NOTE: We're extracting the comment in objdump here, it might be better to calculate it explicitly
    obj_dump_match = re.search(fr"#\s(\d+)\s<{function}", obj_dump)

    if not obj_dump_match:
        raise ValueError("Could not find malloc entry in PLT")

    plt_offset = int(obj_dump_match.group(1), 16)
    print(f"Found PLT offset at {hex(plt_offset)}")
    return plt_offset

def get_prog_address(pid: int) -> int:
    """Get the starting address of a process"""
    with open(f"/proc/{pid}/maps", 'r') as f:
        maps = f.read()
    maps_match = re.search(r"([a-fA-F\d]+)", maps)

    if not maps_match:
        raise ValueError("Could not find memory address of process")

    addr = int(maps_match.group(1), 16)
    print(f"Found process at {hex(addr)}")
    return addr

def run_gdb(pid: int, cmd: str) -> str:
    output = subprocess.run(["gdb", "-p", str(pid), "-ex", cmd, "-batch"], capture_output=True, text=True)
    return output.stdout.strip()

def inject_library(pid: int, path: str):
    output = run_gdb(pid, f'call (void*) dlopen("{path}", 1)')
    handle_match = re.search(r"0x([a-fA-F0-9]+)", output)

    if not handle_match:
        raise ValueError(f"Could not inject {path}")

    handle = int(handle_match.group(1), 16)
    print(f"Injected {path} at {hex(handle)}")
    return handle

def get_function_address(pid: int, function: str) -> int:
    output = run_gdb(pid, f"p {function}")
    func_match = re.search(r"0x([a-fA-F0-9]+)\s<.*>", output)

    if not func_match:
        raise ValueError(f"Could not find memory address of function {function}")

    func_addr = int(func_match.group(1), 16)
    print(f"Found {function} at {hex(func_addr)}")
    return func_addr

def inject_function(plt_addr: int, func_addr: int):
    run_gdb(pid, f"set *(void **) {hex(plt_addr)} = {hex(func_addr)}")


def hook(pid: int):
    # Get the address of the function's plt entry
    prog_addr = get_prog_address(pid)
    malloc_plt_addr = get_plt_offset(pid, "malloc") + prog_addr
    free_plt_addr = get_plt_offset(pid, "free") + prog_addr
    print(f"Malloc PLT entry at {hex(malloc_plt_addr)}")
    print(f"Free PLT entry at {hex(free_plt_addr)}")

    # Inject the dynamic hooking library
    lib_handle = inject_library(pid, LIB_PATH)

    # Get the original & and the hook address
    malloc_real = get_function_address(pid, "malloc")
    malloc_hook = get_function_address(pid, "malloc_hook")
    free_real = get_function_address(pid, "free")
    free_hook = get_function_address(pid, "free_hook")

    # Override the PLT entry for malloc & free with the hook
    inject_function(malloc_plt_addr, malloc_hook)
    inject_function(free_plt_addr, free_hook)

    print("\nPress CTRL+C to detach")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

    # Reset the PLT entry to original malloc & free
    inject_function(malloc_plt_addr, malloc_real)
    inject_function(free_plt_addr, free_real)

    # TODO: Remove the injected library

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pid>")
        exit(1)

    if not os.getuid() == 0:
        print("The program must be run as root")
        exit(1)

    pid = int(sys.argv[1])
    hook(pid)
