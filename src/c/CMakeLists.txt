cmake_minimum_required(VERSION 3.10)
project(pyraview C CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

# Use absolute path for include to avoid relative path headaches
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../include)

# Standard output directories - works perfectly with MinGW/GCC/Clang
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_library(pyraview SHARED pyraview.cpp)
target_link_libraries(pyraview PRIVATE Threads::Threads)

if(NOT WIN32)
    target_link_libraries(pyraview PRIVATE m)
endif()

# Tests
add_executable(run_tests tests/test_main.c)
target_link_libraries(run_tests PRIVATE pyraview)

if(NOT WIN32)
    target_link_libraries(run_tests PRIVATE m)
endif()

# Enable testing must be called before add_test
enable_testing()
add_test(NAME run_tests COMMAND run_tests)
