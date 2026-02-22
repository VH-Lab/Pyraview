cmake_minimum_required(VERSION 3.10)
project(pyraview C)

# Enable CTest
enable_testing()

find_package(OpenMP)

include_directories(../../include)

add_library(pyraview SHARED pyraview.c)

if(OpenMP_C_FOUND)
    target_link_libraries(pyraview PUBLIC OpenMP::OpenMP_C)
else()
    message(WARNING "OpenMP not found. Compiling without parallel support.")
endif()

# Link standard math library
target_link_libraries(pyraview PRIVATE m)

# Tests
add_executable(run_tests tests/test_main.c)
target_link_libraries(run_tests PRIVATE pyraview m)

# Output run_tests to build/tests/
set_target_properties(run_tests PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/tests")

add_test(NAME run_tests COMMAND run_tests)
