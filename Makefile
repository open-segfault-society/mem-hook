# Variables
CXX = g++
CXXFLAGS = -fPIC -shared -Wall
LIB_NAME = hook.so
SRC = hook.cpp
OBJ = $(SRC:.cpp=.o)

# Default target: Build the shared object
all: $(LIB_NAME)

# Rule to build the shared object
$(LIB_NAME): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

# Rule to compile the .cpp source file into an object file (.o)
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean up object and shared object files
clean:
	rm -f $(OBJ) $(LIB_NAME)

.PHONY: all clean

