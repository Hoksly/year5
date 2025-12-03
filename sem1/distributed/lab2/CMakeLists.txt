cmake_minimum_required(VERSION 4.0)
project(lab2)

set(CMAKE_CXX_STANDARD 23)

# Enable CUDA and require CUDAToolkit
enable_language(CUDA)
find_package(CUDAToolkit REQUIRED)

# Sources: main + GPU solver
add_executable(lab2 main.cpp gpu_solver.cu)

# Link CUDA libraries
target_link_libraries(lab2 PRIVATE CUDA::cublas CUDA::cusolver CUDA::cudart)
