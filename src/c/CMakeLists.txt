cmake_minimum_required(VERSION 3.10)
project(pyraview C)

find_package(OpenMP)

include_directories(../../include)

add_library(pyraview SHARED pyraview.c)

if(OpenMP_C_FOUND)
    target_link_libraries(pyraview PUBLIC OpenMP::OpenMP_C)
else()
    message(WARNING "OpenMP not found. Compiling without parallel support.")
endif()

# Link standard math library (not needed on Windows)
if(NOT WIN32)
    target_link_libraries(pyraview PRIVATE m)
endif()

# Tests
add_executable(run_tests tests/test_main.c)
if(NOT WIN32)
    target_link_libraries(run_tests PRIVATE pyraview m)
else()
    target_link_libraries(run_tests PRIVATE pyraview)
endif()

# Use generator expression to handle multi-config paths (Debug/Release) correctly
add_test(NAME run_tests COMMAND $<TARGET_FILE:run_tests>)
