#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

enum TraceType : uint32_t {
    MALLOC = 0,
    NEW = 1,
    NEW_ARRAY = 2,
    NEW_NO_THROW = 3,
    FREE = 4,
    DELETE = 5,
    DELETE_ARRAY = 6,
    DELETE_NO_THROW = 7,
};

struct Trace {
    void* address;           // Address to allocated memory
    uint64_t time;           // Time of allocation
    uint32_t size;           // Size of allocation
    uint32_t backtrace_size; // Backtrace size of allocation

    TraceType type;
    std::array<void*, 20> backtrace_buffer; // Actual backtrace

    Trace(void* alloc_address, uint64_t time, uint32_t size,
          uint32_t backtrace_size, TraceType type,
          std::array<void*, 20> const& backtrace_buffer);
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
    void write(Trace const& trace);

  private:
    Buffer buffer;
};

