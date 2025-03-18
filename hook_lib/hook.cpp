#include <cstdlib>
#include <iostream>
#include <dlfcn.h>

// Define a function pointer for the original functions
void* (*malloc_real)(size_t) = nullptr;
void (*free_real)(void*) = nullptr;

// The hook function for malloc
extern "C" void* malloc_hook(size_t size) {
    std::cout << "malloc hooked: " << size << " bytes" << std::endl;
    return malloc_real(size);  // Call the original malloc
}

extern "C" void* malloc_hook_empty(size_t size) {
    return malloc_real(size);  // Call the original malloc
}

extern "C" void free_hook(void* ptr) {
    std::cout << "free hooked: " << ptr << std::endl;
}

// A function to set the original malloc symbol
void set_original_malloc() {
    malloc_real = (void* (*)(size_t)) dlsym(RTLD_NEXT, "malloc");
    if (!malloc_real) {
        std::cerr << "Failed to find original malloc: " << dlerror() << std::endl;
        exit(1);
    }
}

void set_original_free() {
    free_real = (void (*)(void*)) dlsym(RTLD_NEXT, "free");
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
