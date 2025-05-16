# Compiler and flags
CXX = g++
CXXFLAGS = -fPIC -Wall -Wextra -O2
LDFLAGS = -shared

# Input/output
SRC = timer.cpp
OUT = timer.so

# Default target
all: $(OUT)

# Rule to build the shared library
$(OUT): $(SRC)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^

# Clean up
clean:
	rm -f $(OUT)

