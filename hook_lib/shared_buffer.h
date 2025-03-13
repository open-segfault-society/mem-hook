#pragma once
#include <cstddef>


struct Allocation {
    size_t size;
    double time;
};


#include <cstdint>
#include <string>
class SharedBuffer {
public:
    SharedBuffer();
    ~SharedBuffer();
    void write(Allocation const& alloc);

private:
    char constexpr static MOUNT[] = "/mem_hook";
    size_t static const HEAD_SIZE {8};
    size_t static const DATA_SIZE {4092};
    size_t static const BUFF_SIZE {HEAD_SIZE + DATA_SIZE};

    void* ptr;
    int fd;

    // Ring buffer
    size_t* head;
    size_t* tail;
    Allocation* data_start;
};
