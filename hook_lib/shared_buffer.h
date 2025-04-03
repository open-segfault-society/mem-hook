#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

uint32_t static const BUFFER_SIZE{20};

struct Allocation {
    void* address;                          // Address returned by malloc
    uint32_t size;                          // Size of allocation
    uint32_t time;                          // Time of allocation
    uint32_t backtrace_size;                // Backtrace size of allocation
    std::array<void*, 20> backtrace_buffer; // Actual backtrace

    Allocation(void* alloc_address, uint32_t size, uint32_t time,
               uint32_t backtrace_size, void* (&buffer)[BUFFER_SIZE]);
};

struct Free {
    void* address;                          // Address returned by malloc
    uint32_t time;                          // Time of allocation
    uint32_t backtrace_size;                // Backtrace size of allocation
    std::array<void*, 20> backtrace_buffer; // Actual backtrace

    Free(void* free_ptr, uint32_t time, uint32_t backtrace_size,
         void* (&buffer)[BUFFER_SIZE]);
};

class Buffer {
  public:
    Buffer(const char* mount_point, uint32_t head_size, uint32_t data_size,
           uint32_t buffer_size);
    ~Buffer();

    // Shared memory
    void* memory;
    int fd;

    // Ring buffer
    uint32_t* head;
    uint32_t* tail;
    uint32_t* overflow;
    char* data_start; // char pointer to avoid dividing memory address with 4

    uint32_t head_size;
    uint32_t data_size;
    uint32_t buffer_size;
};

class SharedBuffer {
  public:
    SharedBuffer();
    ~SharedBuffer();
    void write(Allocation const& alloc); // Malloc
    void write(Free const& free);        // Free

  private:
    Buffer malloc_buffer;
    Buffer free_buffer;
};
