import os
import mmap
from time import sleep


class Allocation:
    def __init__(self, size: int, time: int):
        self.size = size
        self.time = time

    def __str__(self):
        return f"Size: {self.size}, Time: {self.time}"


class SharedBuffer:
    MOUNT: str = "/dev/shm/mem_hook"
    size: int

    def __enter__(self):
        # Open the shared memory object
        try:
            # Open the shared memory object (O_RDONLY for read-only access)
            self.fd = os.open(self.MOUNT, os.O_RDWR)
        except OSError as e:
            print(f"Failed to open shared memory: {e}")
            exit(1)

        # Get the size of the shared memory object by using fstat
        self.size = os.fstat(self.fd).st_size

        # Map the shared memory object to the Python process's memory space
        try:
            self.mem = mmap.mmap(self.fd, self.size, access=mmap.ACCESS_WRITE)
        except Exception as e:
            print(f"Failed to map shared memory: {e}")
            os.close(self.fd)
            exit(1)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.fd is None or self.mem is None:
            return

        self.mem.close()
        os.close(self.fd)

    def read_allocation(self, head: int):
        start_address = head * 8 + 8
        size = int.from_bytes(
            self.mem[start_address : start_address + 4], byteorder="little"
        )
        time = int.from_bytes(
            self.mem[start_address + 4 : start_address + 8], byteorder="little"
        )

        return Allocation(size, time)

    def read(self):
        sleep(1)
        print("-----------------------------------------")
        head = int.from_bytes(self.mem[0:4], byteorder="little")
        tail = int.from_bytes(self.mem[4:8], byteorder="little")

        while head != tail:
            print(self.read_allocation(head))
            head = (head + 1) % 32

        self.mem[0:4] = head.to_bytes(4, byteorder="little")
