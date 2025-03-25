#include "shared_buffer.h"
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <execinfo.h>
#include <iostream>

SharedBuffer buffer{};

// Define a function pointer for the original functions
void* (*malloc_real)(size_t) = nullptr;
void (*free_real)(void*) = nullptr;

// Backtrace related values
void* malloc_backtrace_buffer[BUFFER_SIZE];
void* free_backtrace_buffer[BUFFER_SIZE];

// The hook function for malloc
extern "C" void* malloc_hook(uint32_t size) {
    void* const ptr{malloc_real(size)}; // Call the original malloc

    // TODO: test overhead difference of backtrace and backtrace_symbols
    uint32_t backtrace_size = backtrace(malloc_backtrace_buffer, BUFFER_SIZE);
    Allocation alloc{ptr, size, 0, backtrace_size, malloc_backtrace_buffer};
    buffer.write(alloc);

    return ptr;
}

extern "C" void free_hook(void* ptr) {
    uint32_t backtrace_size = backtrace(free_backtrace_buffer, BUFFER_SIZE);
    Free free{ptr, 0, backtrace_size, free_backtrace_buffer};
    buffer.write(free);
    return free_real(ptr);
}

// A function to set the original malloc symbol
void set_original_malloc() {
    malloc_real = (void* (*)(size_t))dlsym(RTLD_NEXT, "malloc");
    if (!malloc_real) {
        std::cerr << "Failed to find original malloc: " << dlerror()
                  << std::endl;
        exit(1);
    }
}

void set_original_free() {
    free_real = (void (*)(void*))dlsym(RTLD_NEXT, "free");
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
