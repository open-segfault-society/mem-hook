#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <malloc.h>
#include <thread>
#include <unistd.h>
#include <vector>

size_t static const NUM_ALLOCS{100000};
size_t static const TRACE_DEPTH{6};

// 16B, 32B, 64B, 128B, 256B, 512B, 1KB, 4KB, 64KB, 1MB
size_t alloc_sizes[] = {16, 32, 64, 128, 256, 512, 1024, 4096, 65536};

/* Run several malloc and return the time it took */
double run_test(size_t alloc_size, size_t num_allocs) {
    void* allocations[num_allocs];
    auto const start{std::chrono::high_resolution_clock::now()};

    for (size_t i = 0; i < num_allocs; i++) {
        allocations[i] = malloc(alloc_size);
    }

    auto const end{std::chrono::high_resolution_clock::now()};
    auto const duration{
        std::chrono::duration_cast<std::chrono::nanoseconds>(end - start)};

    // Free the allocated memory
    for (void* ptr : allocations) {
        free(ptr);
    }

    std::this_thread::sleep_for(std::chrono::seconds(1));

    return duration.count();
}

void print_results(std::vector<double> const& results) {
    int const COL_WIDTH{15};

    std::cout << std::left << std::setw(COL_WIDTH) << "Size (B)" << std::left
              << std::setw(COL_WIDTH) << "Time (ns)" << std::endl;

    for (size_t i = 0; i < results.size(); i++) {
        size_t const size{alloc_sizes[i]};
        double const time{results[i]};

        std::cout << std::left << std::setw(COL_WIDTH) << size << std::left
                  << std::setw(COL_WIDTH) << time << std::endl;
    }

    std::cout << "{";
    for (size_t i = 0; i < results.size(); i++) {
        size_t const size{alloc_sizes[i]};
        double const time{results[i]};
        std::cout << size << ": " << time << ", ";
    }
    std::cout << "}" << std::endl;
}

void do_tests(size_t depth = 0) {
    if (depth > 0) {
        do_tests(depth - 1);
    }
    std::cout << "Press Enter to start the tests..." << std::endl;
    std::cin.get();

    // Disable fastbin caching (makes allocations behave more predictably)
    mallopt(M_MXFAST, 0);
    // Force memory to be returned to the OS immediately
    mallopt(M_TRIM_THRESHOLD, 0);

    // Run allocations before the tests to not get initialisation overhead
    run_test(256, 10000);

    size_t const num_of_tests {sizeof(alloc_sizes) / sizeof(alloc_sizes[0])};
    double results[num_of_tests];

    for (size_t i = 0; i < num_of_tests; i++) {
        results[i] = run_test(alloc_sizes[i], NUM_ALLOCS) / NUM_ALLOCS;
    }

    print_results(std::vector<double>(std::begin(results), std::end(results)));
    std::cin.get();
}
int main (int argc, char *argv[]) {
    if (argc >= 2 && std::stoul(argv[1]) >= TRACE_DEPTH) {
        do_tests(std::stoul(argv[1]) - TRACE_DEPTH);
    } else {
        do_tests();
    }
    return 0;
}
