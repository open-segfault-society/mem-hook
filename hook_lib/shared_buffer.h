#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

uint32_t static const BUFFER_SIZE{20};

struct Allocation {
  void *address;                           // Address returned by malloc
  uint32_t size;                           // Size of allocation
  uint32_t time;                           // Time of allocation
  uint32_t backtrace_size;                 // Backtrace size of allocation
  std::array<void *, 20> backtrace_buffer; // Actual backtrace

  Allocation(void *alloc_address, uint32_t size, uint32_t time,
             uint32_t backtrace_size, void *(&buffer)[BUFFER_SIZE]);
};

class SharedBuffer {
public:
  SharedBuffer();
  ~SharedBuffer();
  void write(Allocation const &alloc); // Malloc
  void write(void *);                  // Free

private:
  char constexpr static ALLOC_MOUNT[] = "/mem_hook_alloc";
  char constexpr static FREE_MOUNT[] = "/mem_hook_free";
  uint32_t static const NUM_ALLOCATIONS{32};
  uint32_t static const HEAD_SIZE{8};
  uint32_t static const MALLOC_DATA_SIZE{NUM_ALLOCATIONS *
                                         sizeof(struct Allocation)};
  uint32_t static const MALLOC_BUFF_SIZE{HEAD_SIZE + MALLOC_DATA_SIZE};

  uint32_t static const FREE_DATA_SIZE{NUM_ALLOCATIONS * sizeof(void *)};
  uint32_t static const FREE_BUFF_SIZE{HEAD_SIZE + FREE_DATA_SIZE};

  // Shared buffer
  void *malloc_memory;
  void *free_memory;
  int fd_malloc;
  int fd_free;

  // Ring buffer
  uint32_t *malloc_head;
  uint32_t *malloc_tail;
  uint32_t *free_head;
  uint32_t *free_tail;
  // char pointer to avoid dividing memory address with 4
  char *malloc_data_start;
  char *free_data_start;
};
