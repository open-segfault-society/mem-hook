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

    *head = 0;
    std::cout << head << std::endl;
    std::cout << *head << std::endl;
    *tail = 0;
    data_start = reinterpret_cast<char*>(memory) + head_size;
}

Buffer::~Buffer() {
    // CLeanup
    munmap(memory, buffer_size);
    close(fd);
}

SharedBuffer::SharedBuffer() {
    std::string malloc_mount = "/mem_hook_alloc";
    uint32_t malloc_num_allocations{1000};
    uint32_t malloc_head_size = 8;
    uint32_t malloc_data_size =
        sizeof(struct Allocation) * malloc_num_allocations;
    uint32_t malloc_buffer_size = malloc_head_size + malloc_data_size;
    malloc_buffer =
        Buffer(malloc_mount, malloc_num_allocations, malloc_head_size,
               malloc_data_size, malloc_buffer_size);

    std::string free_mount = "/mem_hook_free";
    uint32_t free_num_allocations{1000};
    uint32_t free_head_size = 8;
    uint32_t free_data_size = sizeof(struct Free) * free_num_allocations;
    uint32_t free_buffer_size = free_head_size + free_data_size;
    free_buffer = Buffer(free_mount, free_num_allocations, free_head_size,
                         free_data_size, free_buffer_size);
};

SharedBuffer::~SharedBuffer() {
    // Cleanup
    malloc_buffer.~Buffer();
    free_buffer.~Buffer();
}

void SharedBuffer::write(Allocation const& alloc) {
    // std::cout << 12313123 << std::endl;
    // std::cout << malloc_buffer.tail << std::endl;
    // printf("tail: %p, data start: %p\n", malloc_buffer.tail, malloc_buffer.data_start);
    // *(malloc_buffer.head) = 2;
    // std::cout << 123 << std::endl;
    // std::cout << *malloc_buffer.head << std::endl;
    // std::cout << *malloc_buffer.data_start << std::endl;
    // std::cout << *malloc_buffer.tail << std::endl;


    // std::memcpy(malloc_buffer.data_start +
    //                 (*malloc_buffer.tail * sizeof(struct Allocation)),
    //             &alloc, sizeof(alloc));
    // std::cout << 12313123 << std::endl;
    // (*malloc_buffer.tail) =
    //     (*malloc_buffer.tail + 1) %
    //     (malloc_buffer.data_size / sizeof(struct Allocation));
}

void SharedBuffer::write(Free const& free) {
    // std::memcpy(free_buffer.data_start +
    //                 (*free_buffer.tail * sizeof(struct Free)),
    //             &free, sizeof(struct Free));
    // (*free_buffer.tail) =
    //     (*free_buffer.tail + 1) % (free_buffer.data_size / sizeof(struct
    //     Free));
}
