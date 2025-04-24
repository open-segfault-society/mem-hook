#include <iostream>
#include <new>      // for std::nothrow, placement new
#include <cstdlib>  // for std::malloc, std::free

struct MyClass {
    MyClass(int val) : value(val) {
        std::cout << "Constructing MyClass(" << value << ")\n";
    }
    ~MyClass() {
        std::cout << "Destructing MyClass(" << value << ")\n";
    }
    int value;
};

int main() {
    std::cout << "Size of class: " << sizeof(MyClass) << std::endl;
    std::cout << "Press any key to start the test..." << std::endl;
    std::cin.get();
    // 1. Regular single-object new
    MyClass* a = new MyClass(10);
    std::cout << "Regular new: " << a->value << std::endl;
    delete a;

    // 2. Array new
    MyClass* b = new MyClass[3]{ {1}, {2}, {3} };
    std::cout << "Array new: " << b[0].value << ", " << b[1].value << ", " << b[2].value << std::endl;
    delete[] b;

    // 3. Nothrow new
    MyClass* c = new (std::nothrow) MyClass(42);
    delete(c);

    return 0;
}

