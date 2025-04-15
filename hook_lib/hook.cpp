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
void* (*new_real)(size_t) = nullptr;
void* (*array_new_real)(size_t) = nullptr;
void* (*non_throw_new_real)(size_t, const std::nothrow_t&) noexcept = nullptr;
void* (*placement_new_real)(size_t, void*) = nullptr;
void* (*array_placement_new_real)(size_t, void*) = nullptr;

// The hook function for malloc
extern "C" void* malloc_hook(uint32_t size) {
    void* const ptr{malloc_real(size)}; // Call the original malloc

    <<<MALLOC_FILTER_RANGE>>>
    <<<MALLOC_FILTER>>>

    std::array<void*, 20> backtrace_buffer{};

    <<<USE_BACKTRACE_FAST>>>
    <<<USE_BACKTRACE_GLIBC>>>

    Allocation malloc{ptr, size, 0, backtrace_size, backtrace_buffer};
    buffer.write(malloc);
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

void* new_hook(uint32_t size) {
    void* const ptr{new_real(size)};
    return ptr;
}

void* array_new_hook(uint32_t size) {
    void* const ptr{array_new_real(size)};
    return ptr;
}

void* non_throw_new_hook(uint32_t size, const std::nothrow_t& nothrow) {
    void* const ptr{non_throw_new_real(size, nothrow)};
    return ptr;
}

void* placement_new_hook(uint32_t size, void* ptr) {
    void* const new_ptr{placement_new_real(size, ptr)};
    return new_ptr;
}

void* array_placement_new_hook(uint32_t size, void* ptr) {
    void* const new_ptr{array_placement_new_real(size, ptr)};
    return new_ptr;
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

void set_original_new() {
    new_real = (void* (*)(size_t))dlsym(RTLD_NEXT, "_Znwm");
    if (!new_real) {
        std::cerr << "Failed to find original new: " << dlerror() << std::endl;
        exit(1);
    }
}

void set_original_new_array() {
    array_new_real = (void* (*)(size_t))dlsym(RTLD_NEXT, "_Znam");
    if (!array_new_real) {
        std::cerr << "Failed to find original new-array: " << dlerror() << std::endl;
        exit(1);
    }
}

void set_original_new_non_throw() {
    non_throw_new_real = (void* (*)(size_t, const std::nothrow_t&) noexcept)dlsym(RTLD_NEXT, "_ZnwmRKSt9nothrow_t");
    if (!non_throw_new_real) {
        std::cerr << "Failed to find original new-non throw: " << dlerror() << std::endl;
        exit(1);
    }
}

void set_original_placement_new() {
    placement_new_real = (void* (*)(size_t, void*))dlsym(RTLD_NEXT, "_ZnwmPv");
    if (!placement_new_real) {
        std::cerr << "Failed to find original placement new: " << dlerror() << std::endl;
        exit(1);
    }
}

void set_original_placement_new_array() {
    array_placement_new_real = (void* (*)(size_t, void*))dlsym(RTLD_NEXT, "_ZnaPv");
    if (!array_placement_new_real) {
        std::cerr << "Failed to find original placement new array: " << dlerror() << std::endl;
        exit(1);
    }
}

// Entry point for the shared library
__attribute__((constructor)) void initialize() {
    set_original_malloc();
    set_original_free();
    set_original_new();
    set_original_new_array();
    set_original_new_non_throw();
    // set_original_placement_new();
    // set_original_placement_new_array();
}
