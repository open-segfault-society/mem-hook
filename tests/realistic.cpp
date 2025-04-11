#include <random>
#include <iostream>
#include <vector>
#include <chrono>

size_t const NUM_OF_ALLOCS {100000};

std::mt19937 gen(0);  // Seed to get same run each time
std::uniform_int_distribution<int> chance(0, 99);
std::uniform_int_distribution<size_t> small_size(8, 64);
std::uniform_int_distribution<size_t> medium_size(128, 4096);
std::uniform_int_distribution<size_t> large_size(4096, 1024*1024);

size_t get_random_size() {
    int const roll {chance(gen)};
    if (roll < 70) return small_size(gen);
    if (roll < 95) return medium_size(gen);
    return large_size(gen);
}

void simulate() {
    std::vector<void*> keep_alive {};
    std::vector<void*> leaks {};

    for (size_t i = 0; i < NUM_OF_ALLOCS; i++) {
        size_t const size {get_random_size()};
        void* const ptr {malloc(size)};

        if (!ptr) {
            continue;
        }

        if (i % 100 == 0) {
            keep_alive.push_back(ptr);
        } else if (i % 777 == 0) {
            leaks.push_back(ptr);
        } else {
            free(ptr);
        }
        keep_alive.push_back(malloc(get_random_size()));
    }

    for (void* const ptr : keep_alive) {
        free(ptr);
    }
}

int main (int argc, char *argv[]) {
    std::cout << "Press any key to start the test..." << std::endl;
    std::cin.get();

    auto start {std::chrono::steady_clock::now()};
    simulate();
    auto end {std::chrono::steady_clock::now()};

    auto duration {std::chrono::duration_cast<std::chrono::milliseconds>(end - start)};
    std::cout << "Elapsed time: " << duration.count() << " ms" << std::endl;

    return 0;
}
