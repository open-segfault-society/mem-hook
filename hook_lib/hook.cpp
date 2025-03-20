#include "shared_buffer.h"
#include <backtrace.h>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <iostream>

SharedBuffer buffer{};
static void error_callback(void* data, const char* msg, int errnum);
void print_backtrace();

backtrace_state* const state{
    backtrace_create_state(nullptr, 1, error_callback, nullptr)};

// Define a function pointer for the original functions
void* (*malloc_real)(size_t) = nullptr;
void (*free_real)(void*) = nullptr;

// Backtrace related values
void* backtrace_buffer[BUFFER_SIZE];

// The hook function for malloc
extern "C" void* malloc_hook(uint32_t size) {
    void* const ptr{malloc_real(size)}; // Call the original malloc

    // Get allocation time
    // auto now = std::chrono::steady_clock::now();
    // uint32_t now_ns = std::chrono::duration_cast<std::chrono::milliseconds>(
    //                       now.time_since_epoch())
    //                       .count();

    print_backtrace();

    return ptr;
}

extern "C" void free_hook(void* ptr) { return free_real(ptr); }

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

/* BACKTRACE TESTING */

struct TraceHelper {
    size_t frame_count{0};
    size_t max_frames{10};
    uintptr_t frames[10];
};

static void error_callback(void* data, const char* msg, int errnum) {
    std::cerr << "Error in backtrace: " << msg << "(error " << errnum << ")"
              << std::endl;
}

static int simple_callback(void* data, uintptr_t pc) {
    TraceHelper* helper{reinterpret_cast<TraceHelper*>(data)};
    helper->frames[helper->frame_count] = pc;
    helper->frame_count++;

    if (helper->frame_count >= helper->max_frames) {
        return 1;
    }
    return 0;
}

void print_backtrace() {
    if (!state) {
        std::cerr << "Failed to initialize libbacktrace" << std::endl;
        return;
    }

    TraceHelper helper{};

    backtrace_simple(state, 0, simple_callback, error_callback,
                     reinterpret_cast<void*>(&helper));
}

// Entry point for the shared library
__attribute__((constructor)) void initialize() {
    set_original_malloc();
    set_original_free();
}
