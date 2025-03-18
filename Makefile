# Variables
CXX = g++
CXXFLAGS = -fPIC -shared -Wall
LIB_NAME = hook.so
SRC = $(wildcard hook_lib/*.cpp)  
OBJ = $(SRC:.cpp=.o)

# Default target: Build the shared object
all: $(LIB_NAME)

# Rule to build the shared object
$(LIB_NAME): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

# Rule to compile the .cpp source files into object files (.o)
%.o: src/%.cpp  # Ensure object files are compiled from the correct source directory
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean up object and shared object files
clean:
	rm -f $(OBJ) $(LIB_NAME)

.PHONY: all clean

