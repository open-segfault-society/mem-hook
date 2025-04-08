#include "backtrace.h"
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

// The hook function for malloc
extern "C" void* malloc_hook(uint32_t size) {
    void* const ptr{malloc_real(size)}; // Call the original malloc

    <<<MALLOC_FILTER_RANGE>>>
    <<<MALLOC_FILTER>>>

    std::array<void*, 20> backtrace_buffer{};

    <<<USE_BACKTRACE_FAST>>>
    <<<USE_BACKTRACE_GLIBC>>>

    Allocation alloc{ptr, size, 0, backtrace_size, backtrace_buffer};
    buffer.write(alloc);
    return ptr;
}

extern "C" void free_hook(void* ptr) {
    std::array<void*, 20> backtrace_buffer {};

    <<<USE_BACKTRACE_FAST>>>
    <<<USE_BACKTRACE_GLIBC>>>

    Free free{ptr, 0, backtrace_size, backtrace_buffer};
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
