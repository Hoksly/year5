/**
 * @file gpu_solver.cu
 * @brief GPU-accelerated dense linear system solver using NVIDIA cuSOLVER
 *
 * This file implements a dense linear system solver (Ax = b) using
 * LU factorization with partial pivoting on NVIDIA GPUs via the cuSOLVER library.
 */

#include <cuda_runtime.h>
#include <cusolverDn.h>
#include <cublas_v2.h>
#include <cstdio>
#include <cstdlib>
#include <iostream>

// ============================================================================
// Helper Macros for Error Checking
// ============================================================================

#define CUDA_CHECK(call, errorMsg)                                           \
    do {                                                                     \
        cudaStat = (call);                                                   \
        if (cudaStat != cudaSuccess) {                                       \
            std::cerr << "[CUDA ERROR] " << errorMsg                         \
                      << " (code: " << cudaStat << ")" << std::endl;         \
            success = false;                                                 \
            goto cleanup;                                                    \
        }                                                                    \
    } while (0)

#define CUSOLVER_CHECK(call, errorMsg)                                       \
    do {                                                                     \
        cusolverStat = (call);                                               \
        if (cusolverStat != CUSOLVER_STATUS_SUCCESS) {                       \
            std::cerr << "[CUSOLVER ERROR] " << errorMsg                     \
                      << " (code: " << cusolverStat << ")" << std::endl;     \
            success = false;                                                 \
            goto cleanup;                                                    \
        }                                                                    \
    } while (0)

// ============================================================================
// GPU Dense Solver Implementation
// ============================================================================

/**
 * @brief Solves a dense linear system Ax = b using GPU-accelerated LU factorization
 *
 * This function performs LU factorization with partial pivoting using cuSOLVER
 * and then solves the system using forward and backward substitution.
 *
 * @param n              Matrix dimension (n x n square matrix)
 * @param h_A_colmaj     Host pointer to matrix A in column-major format
 * @param h_b            Host pointer to right-hand side vector b
 * @param h_x            Host pointer to output solution vector x
 * @param nrhs           Number of right-hand side vectors (typically 1)
 * @param elapsed_ms_out Output pointer for elapsed GPU computation time in milliseconds
 *
 * @return true if solve was successful, false otherwise
 */
extern "C" bool solve_dense_gpu(
    int n,
    const double* h_A_colmaj,
    const double* h_b,
    double* h_x,
    int nrhs,
    float* elapsed_ms_out
) {
    // ========================================================================
    // Input Validation
    // ========================================================================
    if (n <= 0 || nrhs <= 0) {
        std::cerr << "[GPU SOLVER] Invalid dimensions: n=" << n
                  << ", nrhs=" << nrhs << std::endl;
        return false;
    }

    // ========================================================================
    // Variable Declarations (ALL declared before any goto statements)
    // ========================================================================

    // Success flag
    bool success = true;

    // CUDA/cuSOLVER handles
    cusolverDnHandle_t cusolverHandle = nullptr;
    cublasHandle_t cublasHandle = nullptr;

    // Status codes
    cudaError_t cudaStat = cudaSuccess;
    cusolverStatus_t cusolverStat = CUSOLVER_STATUS_SUCCESS;
    cublasStatus_t cublasStat = CUBLAS_STATUS_SUCCESS;

    // Device memory pointers
    double* d_A = nullptr;          // Device matrix A
    double* d_B = nullptr;          // Device right-hand side / solution
    double* d_workspace = nullptr;  // cuSOLVER workspace
    int* d_pivotArray = nullptr;    // Pivot indices from LU factorization
    int* d_infoArray = nullptr;     // Info output from cuSOLVER

    // Workspace size
    int workspaceSize = 0;

    // Memory sizes
    const size_t matrixSizeBytes = static_cast<size_t>(n) * static_cast<size_t>(n) * sizeof(double);
    const size_t vectorSizeBytes = static_cast<size_t>(n) * static_cast<size_t>(nrhs) * sizeof(double);

    // Timing variables (declared here to avoid goto issues)
    cudaEvent_t timerStart = nullptr;
    cudaEvent_t timerStop = nullptr;
    float elapsedMilliseconds = 0.0f;

    // ========================================================================
    // Initialize cuSOLVER and cuBLAS Handles
    // ========================================================================

    std::cout << "[GPU SOLVER] Initializing CUDA libraries..." << std::endl;

    cusolverStat = cusolverDnCreate(&cusolverHandle);
    if (cusolverStat != CUSOLVER_STATUS_SUCCESS) {
        std::cerr << "[GPU SOLVER] Failed to create cuSOLVER handle" << std::endl;
        return false;
    }

    cublasStat = cublasCreate(&cublasHandle);
    if (cublasStat != CUBLAS_STATUS_SUCCESS) {
        std::cerr << "[GPU SOLVER] Failed to create cuBLAS handle" << std::endl;
        cusolverDnDestroy(cusolverHandle);
        return false;
    }

    // ========================================================================
    // Allocate Device Memory
    // ========================================================================

    std::cout << "[GPU SOLVER] Allocating device memory for " << n << "x" << n
              << " matrix (" << (matrixSizeBytes / (1024.0 * 1024.0)) << " MB)..." << std::endl;

    CUDA_CHECK(
        cudaMalloc(reinterpret_cast<void**>(&d_A), matrixSizeBytes),
        "Failed to allocate device memory for matrix A"
    );

    CUDA_CHECK(
        cudaMalloc(reinterpret_cast<void**>(&d_B), vectorSizeBytes),
        "Failed to allocate device memory for vector B"
    );

    // ========================================================================
    // Copy Data from Host to Device
    // ========================================================================

    std::cout << "[GPU SOLVER] Copying matrix data to GPU..." << std::endl;

    CUDA_CHECK(
        cudaMemcpy(d_A, h_A_colmaj, matrixSizeBytes, cudaMemcpyHostToDevice),
        "Failed to copy matrix A from host to device"
    );

    CUDA_CHECK(
        cudaMemcpy(d_B, h_b, vectorSizeBytes, cudaMemcpyHostToDevice),
        "Failed to copy vector B from host to device"
    );

    // ========================================================================
    // Query and Allocate Workspace for LU Factorization
    // ========================================================================

    std::cout << "[GPU SOLVER] Querying workspace requirements..." << std::endl;

    CUSOLVER_CHECK(
        cusolverDnDgetrf_bufferSize(cusolverHandle, n, n, d_A, n, &workspaceSize),
        "Failed to query workspace size for LU factorization"
    );

    std::cout << "[GPU SOLVER] Workspace size: " << workspaceSize << " elements ("
              << (workspaceSize * sizeof(double) / 1024.0) << " KB)" << std::endl;

    CUDA_CHECK(
        cudaMalloc(reinterpret_cast<void**>(&d_workspace), sizeof(double) * static_cast<size_t>(workspaceSize)),
        "Failed to allocate workspace memory"
    );

    CUDA_CHECK(
        cudaMalloc(reinterpret_cast<void**>(&d_pivotArray), sizeof(int) * static_cast<size_t>(n)),
        "Failed to allocate pivot array memory"
    );

    CUDA_CHECK(
        cudaMalloc(reinterpret_cast<void**>(&d_infoArray), sizeof(int)),
        "Failed to allocate info array memory"
    );

    // ========================================================================
    // Create CUDA Events for Timing
    // ========================================================================

    CUDA_CHECK(cudaEventCreate(&timerStart), "Failed to create start timer event");
    CUDA_CHECK(cudaEventCreate(&timerStop), "Failed to create stop timer event");

    // ========================================================================
    // Perform LU Factorization and Solve (Timed Section)
    // ========================================================================

    std::cout << "[GPU SOLVER] Starting LU factorization and solve..." << std::endl;

    // Record start time
    CUDA_CHECK(cudaEventRecord(timerStart), "Failed to record start event");

    // LU factorization: A = P * L * U
    CUSOLVER_CHECK(
        cusolverDnDgetrf(
            cusolverHandle,
            n,                  // Number of rows
            n,                  // Number of columns
            d_A,                // Matrix to factorize (overwritten with L and U)
            n,                  // Leading dimension of A
            d_workspace,        // Workspace
            d_pivotArray,       // Output: pivot indices
            d_infoArray         // Output: factorization info
        ),
        "LU factorization (dgetrf) failed"
    );

    // Solve the system using the LU factors: L*U*x = P*b
    CUSOLVER_CHECK(
        cusolverDnDgetrs(
            cusolverHandle,
            CUBLAS_OP_N,        // No transpose
            n,                  // Order of matrix A
            nrhs,               // Number of right-hand sides
            d_A,                // LU factors from dgetrf
            n,                  // Leading dimension of A
            d_pivotArray,       // Pivot indices from dgetrf
            d_B,                // Right-hand side (overwritten with solution)
            n,                  // Leading dimension of B
            d_infoArray         // Output: solve info
        ),
        "Linear solve (dgetrs) failed"
    );

    // Record stop time and synchronize
    CUDA_CHECK(cudaEventRecord(timerStop), "Failed to record stop event");
    CUDA_CHECK(cudaEventSynchronize(timerStop), "Failed to synchronize stop event");

    // Calculate elapsed time
    CUDA_CHECK(
        cudaEventElapsedTime(&elapsedMilliseconds, timerStart, timerStop),
        "Failed to calculate elapsed time"
    );

    if (elapsed_ms_out != nullptr) {
        *elapsed_ms_out = elapsedMilliseconds;
    }

    std::cout << "[GPU SOLVER] Factorization and solve completed in "
              << elapsedMilliseconds << " ms" << std::endl;

    // ========================================================================
    // Copy Solution from Device to Host
    // ========================================================================

    std::cout << "[GPU SOLVER] Copying solution back to host..." << std::endl;

    CUDA_CHECK(
        cudaMemcpy(h_x, d_B, vectorSizeBytes, cudaMemcpyDeviceToHost),
        "Failed to copy solution from device to host"
    );

    std::cout << "[GPU SOLVER] Solve completed successfully!" << std::endl;

// ============================================================================
// Cleanup Section
// ============================================================================
cleanup:

    // Destroy timer events
    if (timerStart != nullptr) {
        cudaEventDestroy(timerStart);
    }
    if (timerStop != nullptr) {
        cudaEventDestroy(timerStop);
    }

    // Free device memory
    if (d_A != nullptr) {
        cudaFree(d_A);
    }
    if (d_B != nullptr) {
        cudaFree(d_B);
    }
    if (d_workspace != nullptr) {
        cudaFree(d_workspace);
    }
    if (d_pivotArray != nullptr) {
        cudaFree(d_pivotArray);
    }
    if (d_infoArray != nullptr) {
        cudaFree(d_infoArray);
    }

    // Destroy handles
    if (cusolverHandle != nullptr) {
        cusolverDnDestroy(cusolverHandle);
    }
    if (cublasHandle != nullptr) {
        cublasDestroy(cublasHandle);
    }

    return success;
}
