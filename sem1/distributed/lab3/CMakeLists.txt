cmake_minimum_required(VERSION 3.16)
project(lab3)

set(CMAKE_CXX_STANDARD 17)

# Знаходимо та підключаємо OpenMP
find_package(OpenMP REQUIRED)

add_executable(lab3 main.cpp)

# Лінкуємо OpenMP
target_link_libraries(lab3 PUBLIC OpenMP::OpenMP_CXX)
