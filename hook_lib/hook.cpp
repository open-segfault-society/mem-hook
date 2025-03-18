#include "shared_buffer.h"
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <execinfo.h>
#include <iostream>

SharedBuffer buffer{};

// Define a function pointer for the original functions
void *(*malloc_real)(size_t) = nullptr;
void (*free_real)(void *) = nullptr;

// Backtrace related values
void *backtrace_buffer[BUFFER_SIZE];

// The hook function for malloc
extern "C" void *malloc_hook(uint32_t size) {
  void *const ptr{malloc_real(size)}; // Call the original malloc

  // Get allocation time
  auto now = std::chrono::steady_clock::now();
  uint32_t now_ns = std::chrono::duration_cast<std::chrono::milliseconds>(
                        now.time_since_epoch())
                        .count();

  // Get call stack address and number of addresses
  // TODO: test overhead difference of backtrace and backtrace_symbols
  // uint32_t backtrace_size = backtrace(backtrace_buffer, BUFFER_SIZE);
  // uint32_t backtrace_size = backtrace_symbols(backtrace_buffer, BUFFER_SIZE);
  Allocation alloc{ptr, size, now_ns, backtrace_size, backtrace_buffer};

  buffer.write(alloc);

  return ptr;
}

extern "C" void free_hook(void *ptr) {
  buffer.write(ptr);
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
