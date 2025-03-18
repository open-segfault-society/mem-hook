#include "shared_buffer.h"
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <ostream>
#include <sys/mman.h> // For shm_open, mmap
#include <unistd.h>   // For close

// ===================
//     Allocation
// ===================

Allocation::Allocation(void *alloc_address, uint32_t size, uint32_t time,
                       uint32_t backtrace_size, void *(&buffer)[20])
    : address{alloc_address}, size{size}, time{time},
      backtrace_size{backtrace_size} {
  std::copy(std::begin(buffer), std::end(buffer), backtrace_buffer.begin());
}

// ===================
//       Buffer
// ===================

SharedBuffer::SharedBuffer() {
  // Open the existing shared memory object
  fd_malloc = shm_open(ALLOC_MOUNT, O_CREAT | O_RDWR, 0666);
  if (fd_malloc == -1) {
    perror("shm_open");
    return;
  }
  fd_free = shm_open(FREE_MOUNT, O_CREAT | O_RDWR, 0666);
  if (fd_free == -1) {
    perror("shm_open");
    return;
  }

  // Set the shared memory size
  if (ftruncate(fd_malloc, MALLOC_BUFF_SIZE) == -1) {
    perror("ftruncate");
    return;
  }
  if (ftruncate(fd_free, FREE_BUFF_SIZE) == -1) {
    perror("ftruncate");
    return;
  }

  // Map the shared memory into process address space
  malloc_memory = mmap(nullptr, MALLOC_BUFF_SIZE, PROT_READ | PROT_WRITE,
                       MAP_SHARED, fd_malloc, 0);
  if (malloc_memory == MAP_FAILED) {
    perror("mmap");
    return;
  }
  free_memory = mmap(nullptr, FREE_BUFF_SIZE, PROT_READ | PROT_WRITE,
                     MAP_SHARED, fd_free, 0);
  if (free_memory == MAP_FAILED) {
    perror("mmap");
    return;
  }

  malloc_head = reinterpret_cast<uint32_t *>(malloc_memory);
  malloc_tail = reinterpret_cast<uint32_t *>(malloc_head + 1);
  free_head = reinterpret_cast<uint32_t *>(free_memory);
  free_tail = reinterpret_cast<uint32_t *>(free_head + 1);

  // Assuming same header info for both buffers (atleast in size)
  *malloc_head = 0;
  *malloc_tail = 0;
  malloc_data_start = reinterpret_cast<char *>(malloc_memory) + HEAD_SIZE;

  *free_head = 0;
  *free_tail = 0;
  free_data_start = reinterpret_cast<char *>(free_memory) + HEAD_SIZE;
};

SharedBuffer::~SharedBuffer() {
  // Cleanup
  munmap(malloc_memory, MALLOC_BUFF_SIZE);
  close(fd_malloc);
  munmap(free_memory, FREE_BUFF_SIZE);
  close(fd_free);
}

void SharedBuffer::write(Allocation const &alloc) {
  // TODO: Check if buffer is full?
  // std::cout << sizeof(struct Allocation) << std::endl;
  // std::cout << "Tail: " << *tail << ", Head: " << *head << std::endl;
  std::cout << sizeof(struct Allocation) << std::endl;
  std::memcpy(malloc_data_start + (*malloc_tail * sizeof(struct Allocation)),
              &alloc, sizeof(alloc));
  (*malloc_tail) =
      (*malloc_tail + 1) % (MALLOC_DATA_SIZE / sizeof(struct Allocation));
}

void SharedBuffer::write(void *ptr) {
  std::memcpy(free_data_start + (*free_tail * sizeof(void *)), ptr,
              sizeof(void *));
  (*free_tail) = (*free_tail + 1) % (FREE_DATA_SIZE / sizeof(void *));
}
