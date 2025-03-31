#include "shared_buffer.h"
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <execinfo.h>
#include <iostream>
#include <unordered_map>

SharedBuffer buffer{};
uint64_t total_allocations{0};
uint64_t num_allocations{0};
std::unordered_map<uint64_t, uint64_t> allocations;

// Define a function pointer for the original functions
void *(*malloc_real)(size_t) = nullptr;
void (*free_real)(void *) = nullptr;

// Backtrace related values
void *malloc_backtrace_buffer[BUFFER_SIZE];
void *free_backtrace_buffer[BUFFER_SIZE];

// The hook function for malloc
extern "C" void *malloc_hook(uint32_t size) {
  void *const ptr{malloc_real(size)}; // Call the original malloc

  total_allocations += size;
  num_allocations++;
  allocations[size]++;

  std::cout << "Total size: " << total_allocations
            << ". Num allocations: " << num_allocations << std::endl;

  for (const auto &[key, value] : allocations) {
    std::cout << "Amount: " << key << ". Size: " << value << '\n';
  }
  std::cout << std::endl;

  // Get allocation time
  // auto now = std::chrono::steady_clock::now();
  // uint32_t now_ns = std::chrono::duration_cast<std::chrono::milliseconds>(
  //                       now.time_since_epoch())
  // .count();

  // Get call stack address and number of addresses
  // TODO: test overhead difference of backtrace and backtrace_symbols
  // uint32_t backtrace_size = backtrace(malloc_backtrace_buffer, BUFFER_SIZE);
  // backtrace_symbols(backtrace_buffer, BUFFER_SIZE);

  // Allocation alloc{ptr, size, 0, backtrace_size, malloc_backtrace_buffer};

  // buffer.write(alloc);

  return ptr;
}

extern "C" void free_hook(void *ptr) {
  uint32_t backtrace_size = backtrace(free_backtrace_buffer, BUFFER_SIZE);

  // Get allocation time
  // auto now = std::chrono::steady_clock::now();
  // uint32_t now_ns = std::chrono::duration_cast<std::chrono::milliseconds>(
  //                       now.time_since_epoch())
  // .count();
  Free free{ptr, 0, backtrace_size, free_backtrace_buffer};
  buffer.write(free);
  return free_real(ptr);
}

// A function to set the original malloc symbol
void set_original_malloc() {
  malloc_real = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
  if (!malloc_real) {
    std::cerr << "Failed to find original malloc: " << dlerror() << std::endl;
    exit(1);
  }
}

void set_original_free() {
  free_real = (void (*)(void *))dlsym(RTLD_NEXT, "free");
  if (!free_real) {
    std::cerr << "Failed to find original free: " << dlerror() << std::endl;
    exit(1);
  }
}

// Entry point for the shared library
__attribute__((constructor)) void initialize() {
  set_original_malloc();
  set_original_free();
}
