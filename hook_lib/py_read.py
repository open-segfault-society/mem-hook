import mmap
import os

# Define the shared memory name (must match the one used in the C++ code)
SHM_NAME = '/dev/shm/mem_hook'  # The name of your shared memory object

# Open the shared memory object
try:
    # Open the shared memory object (O_RDONLY for read-only access)
    fd = os.open(SHM_NAME, os.O_RDONLY)
except OSError as e:
    print(f"Failed to open shared memory: {e}")
    exit(1)

# Get the size of the shared memory object by using fstat
size = os.fstat(fd).st_size

# Map the shared memory object to the Python process's memory space
try:
    mem = mmap.mmap(fd, size, access=mmap.ACCESS_READ)
except Exception as e:
    print(f"Failed to map shared memory: {e}")
    os.close(fd)
    exit(1)

# Read from the shared memory (assuming it's an array of integers)
print("Shared Memory Contents:")
for i in range(size // 4):  # Assuming 4 bytes per integer
    # Read 4 bytes at a time (adjust for your actual data type)
    value = int.from_bytes(mem[i*4:i*4+4], byteorder='little')
    print(f"Value {i}: {value}")

# Close the memory map and file descriptor when done
mem.close()
os.close(fd)

