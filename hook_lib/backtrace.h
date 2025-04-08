#pragma once
#include <array>
#include <cstdint>
#include <algorithm>


/**
 * @brief Collects a series of stack frame addresses starting from the current function.
 * 
 * This function walks the stack by following frame pointers.
 * The `skip` parameter specifies how many initial frames to ignore.
 * 
 * @param skip The number of initial stack frames to skip. Typically set to 1 or more 
 *             to exclude `get_stack()` itself from the results.
 *
 * @return std::array<uintptr_t, N> An array containing the collected stack frame addresses.
 *                                  Each pointer represents the return address of a function call.
 * 
 * @note This function relies on frame pointers being present. Ensure compilation uses
 *       `-fno-omit-frame-pointer` for accurate results.
 * @warning Results may be unreliable if the program is heavily optimized or lacks frame pointers.
 */
template <std::size_t N>
inline size_t walk_stack_fp(std::array<uintptr_t, N>& buffer, std::size_t skip) {
    uintptr_t* fp = reinterpret_cast<uintptr_t*>(__builtin_frame_address(0));
    std::size_t i;

    for (i = 0; fp && i < N; ++i) {
        if (i >= skip) {
            buffer[i] = fp[1]; // The return address of the current frame
        }
        fp = reinterpret_cast<uintptr_t*>(fp[0]); // Follow the frame pointer chain

        if (!fp) {
            break;
        }
    }

    return i;
}

template <typename T, std::size_t N>
inline size_t walk_stack_fp(std::array<T, N>& buffer, std::size_t skip) {
    std::array<uintptr_t, 20> temp {};
    size_t const size {walk_stack_fp<20>(temp, skip)};
    std::transform(
        temp.begin(),
        temp.end(),
        buffer.begin(),
        [](uintptr_t ptr) { return reinterpret_cast<T>(ptr); }
    );
    return size;
}

