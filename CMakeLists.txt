cmake_minimum_required(VERSION 3.10)
project(Pyraview)

enable_testing()

# Set global output directories to verify consistent locations
# On Windows, DLLs and EXEs must be in the same folder for runtime linking
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

# Ensure Windows (MSVC) doesn't append Debug/Release subdirectories
foreach(config ${CMAKE_CONFIGURATION_TYPES} "Release" "Debug" "RelWithDebInfo" "MinSizeRel")
    string(TOUPPER "${config}" CONFIG)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${CONFIG} "${CMAKE_BINARY_DIR}/bin")
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_${CONFIG} "${CMAKE_BINARY_DIR}/bin")
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${CONFIG} "${CMAKE_BINARY_DIR}/lib")
endforeach()

add_subdirectory(src/c)
