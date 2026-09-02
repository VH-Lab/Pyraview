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

# MinGW otherwise leaves the DLL depending on libstdc++/libgcc/libwinpthread
# from the toolchain's bin directory. Link them statically so the DLL stands on
# its own: ctypes (which since Python 3.8 does not search PATH for a loaded
# DLL's dependencies) can then load it from anywhere, and the DLL is
# redistributable as-is.
if(MINGW)
    set_target_properties(pyraview PROPERTIES
        LINK_FLAGS "-static -static-libgcc -static-libstdc++")
endif()

# MSVC exports nothing from a DLL without explicit __declspec(dllexport), which
# would leave the Python wheels built by cibuildwheel with an unusable library.
if(WIN32)
    set_target_properties(pyraview PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# When built through scikit-build-core (pip install), drop the library into the
# Python package directory so it ships inside the wheel next to __init__.py,
# where _find_library() looks for it.
if(SKBUILD)
    install(TARGETS pyraview
        LIBRARY DESTINATION ${SKBUILD_PROJECT_NAME}
        RUNTIME DESTINATION ${SKBUILD_PROJECT_NAME}
        ARCHIVE DESTINATION ${SKBUILD_PROJECT_NAME})
endif()

# Tests. Skipped under scikit-build-core: a pip install only needs the library.
if(NOT SKBUILD)
    add_executable(run_tests tests/test_main.c)
    target_link_libraries(run_tests PRIVATE pyraview)

    if(NOT WIN32)
        target_link_libraries(run_tests PRIVATE m)
    endif()

    # Enable testing must be called before add_test
    enable_testing()
    add_test(NAME run_tests COMMAND run_tests)
endif()
