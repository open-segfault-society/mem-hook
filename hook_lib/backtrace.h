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
 *             to exclude `walk_stack_fp()` itself from the results.
 *
 * @return std::array<T, N> An array containing the collected stack frame addresses.
 *                                  Each pointer represents the return address of a function call.
 * 
 * @note This function relies on frame pointers being present. Ensure compilation uses
 *       `-fno-omit-frame-pointer` for accurate results.
 * @warning Results may be unreliable if the program is heavily optimized or lacks frame pointers.
 */
template <typename T, std::size_t N>
inline size_t walk_stack_fp(std::array<T, N>& buffer, std::size_t skip) {
    T* fp = reinterpret_cast<T*>(__builtin_frame_address(0));
    std::size_t i;

    for (i = 0; fp && i < N; ++i) {
        if (i >= skip) {
            buffer[i] = fp[1]; // The return address of the current frame
        }
        fp = reinterpret_cast<T*>(fp[0]); // Follow the frame pointer chain

        if (!fp) {
            break;
        }
    }

    return i;
}

