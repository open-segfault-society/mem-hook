# Variables
CXX = g++
CXXFLAGS = -fPIC -shared -Wall # -g -rdynamic Added flags for debugging and symbol resolution
LIB_NAME = hook.so
SRC = $(wildcard hook_lib/*.cpp)
OBJ = $(SRC:.cpp=.o)

# libbacktrace settings
BACKTRACE_LIB = -lbacktrace

# Default target: Build the shared object
all: $(LIB_NAME)

# Rule to build the shared object
$(LIB_NAME): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(BACKTRACE_LIB)

# Rule to compile the .cpp source files into object files (.o)
%.o: src/%.cpp  # Ensure object files are compiled from the correct source directory
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean up object and shared object files
clean:
	rm -f $(OBJ) $(LIB_NAME)

.PHONY: all clean

