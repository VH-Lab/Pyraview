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

# Ensure executable can find DLLs on Windows (by outputting to same directory)
if(WIN32)
    # On Windows, put everything in same bin directory to find DLLs
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

    # Override for targets
    set_target_properties(pyraview PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    set_target_properties(run_tests PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
else()
    # Output run_tests to build/tests/
    set_target_properties(run_tests PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/tests")
endif()

# Use generator expression to handle multi-config paths (Debug/Release) correctly
add_test(NAME run_tests COMMAND $<TARGET_FILE:run_tests>)
