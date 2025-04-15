import os
import re
import subprocess
from dataclasses import dataclass

from gdb_utils import GdbUtils


def log(msg: str, error=False):
    print(f"[{'X' if error else '+'}] {msg}")


@dataclass
class FunctionHook:
    plt_addr: int
    func_name: str
    hook_name: str
    func_addr: int = -1
    hook_addr: int = -1


@dataclass
class HookDescriptor:
    hooks: list[FunctionHook]
    pid: int

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        for hook in self.hooks:
            try:
                GdbUtils.inject_function(self.pid, hook.func_addr, hook.plt_addr)
                log(f"Set PLT entry {hex(hook.plt_addr)} to {hex(hook.func_addr)}")
                log(f"Restored {hook.func_name}")
            except Exception as e:
                log(f"Failed to restore {hook.func_name}: {e}", True)


class HookManager:
    DEFAULT_HOOK_SUFFIX = "_hook"
    LIB_NAME: str = "hook.so"

    hooks: list[FunctionHook] = []

    process_path: str
    lib_path: str
    obj_dump: str
    address: int

    def __init__(self, pid: int, debug=True) -> None:
        self.pid = pid
        self.debug = debug

        try:
            self.process_path = self._get_process_path(self.pid)
            self.lib_path = self._get_lib_path()
            self.address = self._get_process_address(self.pid)
            self.obj_dump = self._get_obj_dump(self.process_path)
        except Exception as e:
            self._log(str(e), True)
            exit(1)

    def register_hook(self, func_name: str, hook_name: str = "") -> None:
        if not hook_name:
            hook_name = func_name + self.DEFAULT_HOOK_SUFFIX

        try:
            print(f"func_name: {func_name}")
            plt_addr: int = self._get_plt_offset(func_name) + self.address
            self.hooks.append(FunctionHook(plt_addr, func_name, hook_name))
            self._log(f"Registered hook {hook_name} on {func_name}")
        except Exception as e:
            self._log(str(e), True)

    def inject(self) -> HookDescriptor:
        # Inject the dynamic hooking library
        _ = self._inject_library(self.pid, self.lib_path)

        hook_names = []
        for hook in self.hooks:
            try:
                print(hook.func_name, hook.hook_name)
                hook.func_addr = self._get_function_address(self.pid, hook.func_name)
                hook.hook_addr = self._get_function_address(self.pid, hook.hook_name)
                self._inject_function(self.pid, hook.plt_addr, hook.hook_addr)
                hook_names.append(hook.func_name)
            except Exception as e:
                self._log(str(e), True)

        num = len(hook_names)
        plural = "s" if len(hook_names) > 1 else ""
        names = ", ".join(hook_names)
        self._log(f"Hooking {num} function{plural}... ({names})")
        hd = HookDescriptor(self.hooks, self.pid)
        return hd

    def _log(self, msg: str, error=False) -> None:
        if self.debug:
            log(msg, error)

    def _get_lib_path(self) -> str:
        path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(path, self.LIB_NAME)

    def _get_process_path(self, pid: int) -> str:
        output = subprocess.run(
            ["readlink", "-f", f"/proc/{pid}/exe"], capture_output=True, text=True
        )
        if not output.stdout:
            raise ValueError(f"Could not find the program path for pid {pid}")
        path = output.stdout.strip()
        self._log(f"Found path for pid {pid}: {path}")
        return path

    def _get_obj_dump(self, path: str) -> str:
        output = subprocess.run(["objdump", "-d", path], capture_output=True, text=True)
        return output.stdout.strip()

    def _get_process_address(self, pid: int) -> int:
        """Get the starting address of a process"""
        with open(f"/proc/{pid}/maps", "r") as f:
            maps = f.read()
        maps_match = re.search(r"([a-fA-F\d]+)", maps)

        if not maps_match:
            raise ValueError(f"Could not find memory address of process {pid}")

        addr = int(maps_match.group(1), 16)
        self._log(f"Found process {pid} at {hex(addr)}")
        return addr

    def _get_plt_offset(self, func_name: str) -> int:
        """Get the offset of the function entry in PLT"""
        # NOTE: We're extracting the comment in objdump here, it might be better to calculate it explicitly
        obj_dump_match = re.search(rf"#\s([a-fA-F\d]+)\s<{func_name}", self.obj_dump)
        print(f"obj_dump_match: {obj_dump_match}")

        if not obj_dump_match:
            raise ValueError(f"Could not find {func_name} entry in PLT")

        plt_offset = int(obj_dump_match.group(1), 16)
        self._log(f"Found {func_name} PLT offset at {hex(plt_offset)}")
        return plt_offset

    def _get_function_address(self, pid: int, func_name: str) -> int:
        func_addr = GdbUtils.get_function_address(pid, func_name)
        self._log(f"Found {func_name} at {hex(func_addr)}")
        return func_addr

    def _inject_library(self, pid: int, path: str):
        handle = GdbUtils.inject_library(pid, path)
        self._log(f"Injected {path} at {hex(handle)}")
        return handle

    def _inject_function(self, pid: int, plt_addr: int, func_addr: int):
        GdbUtils.inject_function(pid, plt_addr, func_addr)
        self._log(f"Set PLT entry {hex(plt_addr)} to {hex(func_addr)}")


if __name__ == "__main__":
    hm = HookManager(124168)
    hm.register_hook("malloc")
    hm.register_hook("fraaee")

    with hm.inject() as f:
        pass
