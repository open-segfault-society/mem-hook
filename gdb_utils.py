import re
import subprocess


class GdbUtils:
    @staticmethod
    def run_gdb(pid: int, cmd: str) -> str:
        output = subprocess.run(
            ["gdb", "-p", str(pid), "-ex", cmd, "-batch"],
            capture_output=True,
            text=True,
        )
        if not output.stdout:
            raise ValueError(f"Could not attach GDB to process {pid}")
        return output.stdout.strip()

    @staticmethod
    def get_function_address(pid: int, func_name: str) -> int:
        output = GdbUtils.run_gdb(pid, f"p {func_name}")
        func_match = re.search(r"0x([a-fA-F0-9]+)\s<.*>", output)

        if not func_match:
            raise ValueError(f"Could not find memory address of function {func_name}")

        func_addr = int(func_match.group(1), 16)
        return func_addr

    @staticmethod
    def inject_library(pid: int, path: str):

        output = GdbUtils.run_gdb(pid, f'call (void*) dlopen("{path}", 1)')
        handle_match = re.search(r"0x([a-fA-F0-9]+)", output)

        if not handle_match:
            raise ValueError(f"Could not inject {path}")

        handle = int(handle_match.group(1), 16)
        return handle

    @staticmethod
    def inject_function(pid: int, plt_addr: int, func_addr: int):
        GdbUtils.run_gdb(pid, f"set *(void **) {hex(plt_addr)} = {hex(func_addr)}")
