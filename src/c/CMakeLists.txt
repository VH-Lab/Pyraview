cmake_minimum_required(VERSION 3.10)
project(pyraview C)

find_package(OpenMP)

# Use absolute path for include to avoid relative path headaches
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../include)

# --- OUTPUT DIRECTORY FIX ---
# This forces Windows/MSVC to put everything in /bin instead of /bin/Release
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

foreach(config ${CMAKE_CONFIGURATION_TYPES})
    string(TOUPPER ${config} CONFIG)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${CONFIG} ${CMAKE_BINARY_DIR}/bin)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_${CONFIG} ${CMAKE_BINARY_DIR}/bin)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${CONFIG} ${CMAKE_BINARY_DIR}/bin)
endforeach()
# -----------------------------

add_library(pyraview SHARED pyraview.c)

if(OpenMP_C_FOUND)
    target_link_libraries(pyraview PUBLIC OpenMP::OpenMP_C)
else()
    message(WARNING "OpenMP not found. Compiling without parallel support.")
endif()

if(NOT WIN32)
    target_link_libraries(pyraview PRIVATE m)
endif()

# Tests
add_executable(run_tests ALL tests/test_main.c)
set_target_properties(run_tests PROPERTIES EXCLUDE_FROM_ALL FALSE)
target_link_libraries(run_tests PRIVATE pyraview)

if(NOT WIN32)
    target_link_libraries(run_tests PRIVATE m)
endif()

# Enable testing must be called before add_test
enable_testing()
add_test(NAME run_tests COMMAND $<TARGET_FILE:run_tests>)
