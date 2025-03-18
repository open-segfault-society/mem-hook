import os
import mmap
from time import sleep

# Constants
HEAD_SIZE: int = 8
ALLOCATION_SIZE: int = (
    24 + 8 * 20
)  # Accounts for inner padding, currently no padding between allocations


class Allocation:
    def __init__(
        self,
        pointer: int,
        size: int,
        time: int,
        backtrace_size: int,
        backtraces: list[int],
    ):
        self.pointer = pointer
        self.size = size
        self.time = time
        self.backtrace_size = backtrace_size
        self.backtraces = backtraces

    def __str__(self):
        addresses = [hex(value) for value in self.backtraces]
        return f"Address: {hex(self.pointer)}, Size: {self.size}, Time: {self.time}, Backtrace size: {self.backtrace_size}, Backtrace: {addresses}"


class SharedBuffer:
    MALLOC_MOUNT: str = "/dev/shm/mem_hook_alloc"
    FREE_MOUNT: str = "/dev/shm/mem_hook_free"
    size: int

    def __enter__(self):
        # Open the shared memory object
        try:
            # Open the shared memory object (O_RDWR for read-write access)
            self.malloc_fd = os.open(self.MALLOC_MOUNT, os.O_RDWR)
            self.free_fd = os.open(self.FREE_MOUNT, os.O_RDWR)
        except OSError as e:
            print(f"Failed to open shared memory: {e}")
            exit(1)

        # Get the size of the shared memory object by using fstat
        self.malloc_size = os.fstat(self.malloc_fd).st_size
        self.free_size = os.fstat(self.free_fd).st_size

        # Map the shared memory object to the Python process's memory space
        try:
            self.malloc_mem = mmap.mmap(
                self.malloc_fd, self.malloc_size, access=mmap.ACCESS_WRITE
            )
            self.free_mem = mmap.mmap(
                self.free_fd, self.free_size, access=mmap.ACCESS_WRITE
            )
        except Exception as e:
            print(f"Failed to map shared memory: {e}")
            os.close(self.malloc_fd)
            os.close(self.free_fd)
            exit(1)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.malloc_fd is None or self.malloc_mem is None:
            return
        if self.free_fd is None or self.free_mem is None:
            return

        self.malloc_mem.close()
        os.close(self.malloc_fd)
        self.free_mem.close()
        os.close(self.free_fd)

    def read_backtraces(self, start_address, backtrace_size) -> list[int]:
        if backtrace_size == 0:
            return []

        backtraces = []
        read_pointers = 0

        while read_pointers != backtrace_size:
            backtraces.append(
                int.from_bytes(
                    self.malloc_mem[
                        start_address
                        + read_pointers * 8 : start_address
                        + (read_pointers + 1) * 8
                    ],
                    byteorder="little",
                )
            )
            read_pointers += 1

        return backtraces

    def read_allocation(self, head: int):
        start_address = head * ALLOCATION_SIZE + HEAD_SIZE
        pointer = int.from_bytes(
            self.malloc_mem[start_address : start_address + 8], byteorder="little"
        )
        size = int.from_bytes(
            self.malloc_mem[start_address + 8 : start_address + 12], byteorder="little"
        )
        time = int.from_bytes(
            self.malloc_mem[start_address + 12 : start_address + 16], byteorder="little"
        )
        backtrace_size = int.from_bytes(
            self.malloc_mem[start_address + 16 : start_address + 20], byteorder="little"
        )

        backtraces = self.read_backtraces(start_address + 24, backtrace_size)

        return Allocation(pointer, size, time, backtrace_size, backtraces)

    def read_free(self, head: int) -> int:
        # assumes 8 bytes pointers aka 64-bit system
        free_address = head * 8 + HEAD_SIZE
        return int.from_bytes(
            self.free_mem[free_address : free_address + 8], byteorder="little"
        )

    def read(self):
        # =================
        #       MALLOC
        # =================
        malloc_head = int.from_bytes(self.malloc_mem[0:4], byteorder="little")
        malloc_tail = int.from_bytes(self.malloc_mem[4:8], byteorder="little")

        while malloc_head != malloc_tail:
            print(self.read_allocation(malloc_head))
            malloc_head = (malloc_head + 1) % 32

        self.malloc_mem[0:4] = malloc_head.to_bytes(4, byteorder="little")

        # =================
        #       FREE
        # =================

        free_head = int.from_bytes(self.free_mem[0:4], byteorder="little")
        free_tail = int.from_bytes(self.free_mem[4:8], byteorder="little")

        while free_head != free_tail:
            print(hex(self.read_free(free_head)))
            free_head = (free_head + 1) % 32

        self.free_mem[0:4] = free_head.to_bytes(4, byteorder="little")
