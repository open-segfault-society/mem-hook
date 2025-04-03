#include "shared_buffer.h"
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <ostream>
#include <sys/mman.h> // For shm_open, mmap
#include <unistd.h>   // For close

// ===================
//     Allocation
//         &
//       Free
// ===================

Allocation::Allocation(void* alloc_address, uint32_t size, uint32_t time,
                       uint32_t backtrace_size, void* (&buffer)[20])
    : address{alloc_address}, size{size}, time{time},
      backtrace_size{backtrace_size} {
    std::copy(std::begin(buffer), std::end(buffer), backtrace_buffer.begin());
}

Free::Free(void* free_ptr, uint32_t time, uint32_t backtrace_size,
           void* (&buffer)[20])
    : address{free_ptr}, time{time}, backtrace_size{backtrace_size} {
    std::copy(std::begin(buffer), std::end(buffer), backtrace_buffer.begin());
}

// ===================
//       Buffer
// ===================

Buffer::Buffer(std::string mount_point, uint32_t num_allocations,
               uint32_t head_size, uint32_t data_size, uint32_t buffer_size)
    : num_allocations{num_allocations}, head_size{head_size},
      data_size{data_size}, buffer_size{buffer_size} {

    // Open the existing shared memory object
    fd = shm_open(mount_point.c_str(), O_CREAT | O_RDWR, 0666);
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

SharedBuffer::SharedBuffer()
    : malloc_buffer("/mem_hook_alloc", 1000, 12, sizeof(Allocation) * 1000,
                    8 + sizeof(Allocation) * 1000),
      free_buffer("/mem_hook_free", 1000, 12, sizeof(Free) * 1000,
                  8 + sizeof(Free) * 1000){};

SharedBuffer::~SharedBuffer() {
    // Cleanup
    malloc_buffer.~Buffer();
    free_buffer.~Buffer();
}

void SharedBuffer::write(Allocation const& alloc) {
    uint32_t const next_tail =
        (*malloc_buffer.tail + 1) %
        (malloc_buffer.data_size / sizeof(struct Allocation));

    if (next_tail == *malloc_buffer.head) {
        *malloc_buffer.overflow = 1;
        return;
    }

    std::memcpy(malloc_buffer.data_start +
                    (*malloc_buffer.tail * sizeof(struct Allocation)),
                &alloc, sizeof(alloc));
    (*malloc_buffer.tail) = next_tail;
}

void SharedBuffer::write(Free const& free) {
    uint32_t const next_tail = (*free_buffer.tail + 1) % (free_buffer.data_size / sizeof(struct Free));

    if (next_tail == *free_buffer.head) {
        *free_buffer.overflow = 1;
        return;
    }

    std::memcpy(free_buffer.data_start +
                    (*free_buffer.tail * sizeof(struct Free)),
                &free, sizeof(struct Free));
    (*free_buffer.tail) = next_tail;
}
