#include <cuda_runtime.h>
#include <cusolverDn.h>
#include <cublas_v2.h>
#include <cstdio>
#include <cstdlib>
#include <iostream>

// Simple GPU dense solver using cuSOLVER (LU factorization + solve)

extern "C" bool solve_dense_gpu(int n, const double* h_A_colmaj, const double* h_b, double* h_x, int nrhs, float* elapsed_ms_out) {
    if (n <= 0 || nrhs <= 0) return false;

    cusolverDnHandle_t cusolverH = nullptr;
    cublasHandle_t cublasH = nullptr;
    cudaError_t cudaStat = cudaSuccess;
    cusolverStatus_t cusolverStat = CUSOLVER_STATUS_SUCCESS;
    cublasStatus_t cublasStat = CUBLAS_STATUS_SUCCESS;

    cusolverStat = cusolverDnCreate(&cusolverH);
    if (cusolverStat != CUSOLVER_STATUS_SUCCESS) {
        std::cerr << "cusolverDnCreate failed\n";
        return false;
    }
    cublasStat = cublasCreate(&cublasH);
    if (cublasStat != CUBLAS_STATUS_SUCCESS) {
        std::cerr << "cublasCreate failed\n";
        cusolverDnDestroy(cusolverH);
        return false;
    }

    double* d_A = nullptr;
    double* d_B = nullptr;
    int* d_ipiv = nullptr;
    int* d_info = nullptr;
    double* d_work = nullptr;
    int lwork = 0;

    size_t matrixBytes = size_t(n) * size_t(n) * sizeof(double);
    size_t rhsBytes = size_t(n) * size_t(nrhs) * sizeof(double);

    cudaStat = cudaMalloc((void**)&d_A, matrixBytes);
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMalloc d_A failed\n"; goto cleanup; }
    cudaStat = cudaMalloc((void**)&d_B, rhsBytes);
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMalloc d_B failed\n"; goto cleanup; }

    cudaStat = cudaMemcpy(d_A, h_A_colmaj, matrixBytes, cudaMemcpyHostToDevice);
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMemcpy H->D A failed\n"; goto cleanup; }
    cudaStat = cudaMemcpy(d_B, h_b, rhsBytes, cudaMemcpyHostToDevice);
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMemcpy H->D B failed\n"; goto cleanup; }

    cusolverStat = cusolverDnDgetrf_bufferSize(cusolverH, n, n, d_A, n, &lwork);
    if (cusolverStat != CUSOLVER_STATUS_SUCCESS) { std::cerr << "cusolverDnDgetrf_bufferSize failed\n"; goto cleanup; }

    cudaStat = cudaMalloc((void**)&d_work, sizeof(double) * size_t(lwork));
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMalloc d_work failed\n"; goto cleanup; }

    cudaStat = cudaMalloc((void**)&d_ipiv, sizeof(int) * size_t(n));
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMalloc d_ipiv failed\n"; goto cleanup; }

    cudaStat = cudaMalloc((void**)&d_info, sizeof(int));
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMalloc d_info failed\n"; goto cleanup; }

    // Timing with CUDA events
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    cudaEventRecord(start);

    // LU factorization
    cusolverStat = cusolverDnDgetrf(cusolverH, n, n, d_A, n, d_work, d_ipiv, d_info);
    if (cusolverStat != CUSOLVER_STATUS_SUCCESS) { std::cerr << "cusolverDnDgetrf failed\n"; goto cleanup; }

    // Solve
    cusolverStat = cusolverDnDgetrs(cusolverH, CUBLAS_OP_N, n, nrhs, d_A, n, d_ipiv, d_B, n, d_info);
    if (cusolverStat != CUSOLVER_STATUS_SUCCESS) { std::cerr << "cusolverDnDgetrs failed\n"; goto cleanup; }

    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float milliseconds = 0;
    cudaEventElapsedTime(&milliseconds, start, stop);
    if (elapsed_ms_out) *elapsed_ms_out = milliseconds;

    // Copy solution back
    cudaStat = cudaMemcpy(h_x, d_B, rhsBytes, cudaMemcpyDeviceToHost);
    if (cudaStat != cudaSuccess) { std::cerr << "cudaMemcpy D->H x failed\n"; goto cleanup; }

    // Success
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

cleanup:
    if (d_A) cudaFree(d_A);
    if (d_B) cudaFree(d_B);
    if (d_work) cudaFree(d_work);
    if (d_ipiv) cudaFree(d_ipiv);
    if (d_info) cudaFree(d_info);
    if (cusolverH) cusolverDnDestroy(cusolverH);
    if (cublasH) cublasDestroy(cublasH);

    return true;
}

