#include "shared_buffer.h"
#include <cstring>
#include <fcntl.h>
#include <sys/mman.h> // For shm_open, mmap
#include <unistd.h>   // For close

SharedBuffer::SharedBuffer() {
    // Open the existing shared memory object
    fd = shm_open(MOUNT, O_CREAT | O_RDWR, 0666);
    if (fd == -1) {
        perror("shm_open");
        return;
    }

    // Set the shared memory size
    if (ftruncate(fd, BUFF_SIZE) == -1) {
        perror("ftruncate");
        return;
    }

    // Map the shared memory into process address space
    ptr = mmap(nullptr, BUFF_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        perror("mmap");
        return;
    }

    head = reinterpret_cast<size_t*>(ptr);
    tail = reinterpret_cast<size_t*>(head + 1);

    *head = 0;
    *tail = 0;
    data_start = reinterpret_cast<Allocation*>(head + HEAD_SIZE);
};

SharedBuffer::~SharedBuffer() {
    // Cleanup
    munmap(ptr, BUFF_SIZE);
    close(fd);
}

void SharedBuffer::write(Allocation const& alloc) {
    // TODO: Check if buffer is full?
    (*tail) = (*tail + 1) % DATA_SIZE;
    std::memcpy(data_start + *tail, &alloc, sizeof(alloc));
}
