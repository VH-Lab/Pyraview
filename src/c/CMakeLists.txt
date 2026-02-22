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

# Link standard math library
target_link_libraries(pyraview PRIVATE m)
