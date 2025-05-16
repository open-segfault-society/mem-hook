#include <chrono>
#include <dlfcn.h>
#include <iostream>
#include <stdio.h>
#include <unistd.h>

std::chrono::time_point<std::chrono::high_resolution_clock> start_time;

__attribute__((constructor)) void on_start() {
    fprintf(stderr, "[timer] Press any key to start...\n");
    std::cin.get();
    start_time = std::chrono::high_resolution_clock::now();
}

__attribute__((destructor)) void cleanup() {
    auto const end_time {std::chrono::high_resolution_clock::now()};
    double const elapsed {
        std::chrono::duration<double, std::milli>(end_time - start_time)
            .count()
    };
    std::cout << "[timer] Time elapsed: " << elapsed << " ms." << std::endl;
}
