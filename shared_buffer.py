import os
import mmap


class SharedBuffer:
    MOUNT: str = "/dev/shm/mem_hook"
    size: int

    def __enter__(self):
        # Open the shared memory object
        try:
            # Open the shared memory object (O_RDONLY for read-only access)
            self.fd = os.open(self.MOUNT, os.O_RDONLY)
        except OSError as e:
            print(f"Failed to open shared memory: {e}")
            exit(1)

        # Get the size of the shared memory object by using fstat
        self.size = os.fstat(self.fd).st_size

        # Map the shared memory object to the Python process's memory space
        try:
            self.mem = mmap.mmap(self.fd, self.size, access=mmap.ACCESS_READ)
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

    def read(self):
        for i in range(32):  # Assuming 4 bytes per integer
            # Read 4 bytes at a time (adjust for your actual data type)
            value = int.from_bytes(self.mem[i*4:i*4+4], byteorder='little')
            print(f"Value {i}: {value}")
