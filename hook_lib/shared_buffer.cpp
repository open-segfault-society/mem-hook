#include "shared_buffer.h"
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <ostream>
#include <sys/mman.h> // For shm_open, mmap
#include <unistd.h>   // For close

Trace::Trace(void* address, uint64_t time, uint32_t size,
             uint32_t backtrace_size, TraceType type,
             std::array<void*, 20> const& backtrace_buffer)
    : address{address}, time{time}, size{size}, backtrace_size{backtrace_size},
      type{type}, backtrace_buffer{backtrace_buffer} {}

Buffer::Buffer(const char* mount_point, uint32_t head_size, uint32_t data_size,
               uint32_t buffer_size)
    : head_size{head_size}, data_size{data_size}, buffer_size{buffer_size} {

    // Open the existing shared memory object
    fd = shm_open(mount_point, O_CREAT | O_RDWR, 0666);
    if (fd == -1) {
        perror("shm_open");
        return;
    }

    // Set the shared memory size
    if (ftruncate(fd, buffer_size) == -1) {
        perror("ftruncate");
        return;
    }

    // Map the shared memory into process address space
    memory =
        mmap(nullptr, buffer_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (memory == MAP_FAILED) {
        perror("mmap");
        return;
    }

    head = reinterpret_cast<uint32_t*>(memory);
    tail = reinterpret_cast<uint32_t*>(head + 1);
    overflow = reinterpret_cast<uint32_t*>(head + 2);
    *head = 0;
    *tail = 0;
    *overflow = 0;
    data_start = reinterpret_cast<char*>(memory) + head_size;
}

Buffer::~Buffer() {
    // CLeanup
    munmap(memory, buffer_size);
    close(fd);
}

SharedBuffer::SharedBuffer() : <<<BUFFER>>> {};

SharedBuffer::~SharedBuffer() {
    // Cleanup
    buffer.~Buffer();
}

void SharedBuffer::write(Trace const& trace) {
    uint32_t const next_tail =
        (*buffer.tail + 1) % (buffer.data_size / sizeof(struct Trace));

    if (next_tail == *buffer.head) {
        *buffer.overflow = 1;
        return;
    }

    std::memcpy(buffer.data_start + (*buffer.tail * sizeof(struct Trace)),
                &trace, sizeof(struct Trace));
    (*buffer.tail) = next_tail;
}
