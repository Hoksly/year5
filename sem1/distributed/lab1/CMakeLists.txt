cmake_minimum_required(VERSION 4.0)
project(lab1)

set(CMAKE_CXX_STANDARD 23)

find_package(MPI REQUIRED)
add_executable(lab1 main.cpp)
if(MPI_CXX_FOUND)
    target_link_libraries(lab1 PUBLIC MPI::MPI_CXX)
endif()
