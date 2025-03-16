#pragma once
#include <cstddef>
#include <cstdint>
#include <string>

struct Allocation {
  uint32_t size;
  uint32_t time;
};

class SharedBuffer {
public:
  SharedBuffer();
  ~SharedBuffer();
  void write(Allocation const &alloc);

private:
  char constexpr static MOUNT[] = "/mem_hook";
  uint32_t static const HEAD_SIZE{8};
  uint32_t static const DATA_SIZE{32 * sizeof(struct Allocation)};
  uint32_t static const BUFF_SIZE{HEAD_SIZE + DATA_SIZE};

  void *ptr;
  int fd;

  // Ring buffer
  uint32_t *head;
  uint32_t *tail;
  char *data_start; // char pointer to avoid dividing memory address with 4
};
