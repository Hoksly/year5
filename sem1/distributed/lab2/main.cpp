#include <bits/stdc++.h>

using namespace std;

// ============================================================================
// Data Structures
// ============================================================================

/**
 * @brief Coordinate format entry for sparse matrices
 */
struct CoordinateEntry {
    int row;
    int column;
    double value;
};

// ============================================================================
// Matrix Market File Reader
// ============================================================================

/**
 * @brief Reads Matrix Market format files and converts to COO format
 */
class MatrixMarketReader {
public:
    /**
     * @brief Read a Matrix Market file into coordinate format
     * @param filePath Path to the .mtx file
     * @param numberOfRows Output: number of rows
     * @param numberOfColumns Output: number of columns
     * @param coordinateEntries Output: vector of coordinate entries
     * @return true if successful, false otherwise
     */
    static bool readMatrixMarketFile(
        const string& filePath,
        int& numberOfRows,
        int& numberOfColumns,
        vector<CoordinateEntry>& coordinateEntries
    ) {
        ifstream inputFile(filePath);
        if (!inputFile) {
            return false;
        }

        string currentLine;
        bool isCoordinateFormat = false;
        bool isPatternMatrix = false;
        bool isRealMatrix = false;
        bool isSymmetricMatrix = false;

        // Parse header line
        if (!getline(inputFile, currentLine)) {
            return false;
        }

        parseHeaderLine(currentLine, isCoordinateFormat, isPatternMatrix,
                       isRealMatrix, isSymmetricMatrix);

        // Skip comment lines and read dimensions
        while (getline(inputFile, currentLine)) {
            if (currentLine.empty() || currentLine[0] == '%') {
                continue;
            }

            // Parse dimensions line
            stringstream dimensionStream(currentLine);
            int matrixRows, matrixColumns, numberOfNonZeros;

            if (!(dimensionStream >> matrixRows >> matrixColumns >> numberOfNonZeros)) {
                continue;
            }

            numberOfRows = matrixRows;
            numberOfColumns = matrixColumns;
            coordinateEntries.clear();
            coordinateEntries.reserve(max(0, numberOfNonZeros));

            // Read entries
            readCoordinateEntries(inputFile, numberOfNonZeros, isPatternMatrix,
                                 isSymmetricMatrix, coordinateEntries);

            return true;
        }

        return false;
    }

private:
    /**
     * @brief Parse the Matrix Market header line
     */
    static void parseHeaderLine(
        const string& headerLine,
        bool& isCoordinateFormat,
        bool& isPatternMatrix,
        bool& isRealMatrix,
        bool& isSymmetricMatrix
    ) {
        stringstream headerStream(headerLine);
        string token;
        headerStream >> token;

        if (token == "%%MatrixMarket") {
            string objectType, formatType, fieldType, symmetryType;

            if (headerStream >> objectType >> formatType >> fieldType >> symmetryType) {
                isCoordinateFormat = (formatType == "coordinate");
                isPatternMatrix = (fieldType == "pattern");
                isRealMatrix = (fieldType == "real" || fieldType == "integer");
                isSymmetricMatrix = (symmetryType == "symmetric" ||
                                    symmetryType == "hermitian");
            }
        }
    }

    /**
     * @brief Read coordinate entries from file
     */
    static void readCoordinateEntries(
        ifstream& inputFile,
        int numberOfNonZeros,
        bool isPatternMatrix,
        bool isSymmetricMatrix,
        vector<CoordinateEntry>& coordinateEntries
    ) {
        string currentLine;

        for (int entryIndex = 0; entryIndex < numberOfNonZeros; ) {
            if (!getline(inputFile, currentLine)) {
                break;
            }

            if (currentLine.empty() || currentLine[0] == '%') {
                continue;
            }

            stringstream entryStream(currentLine);
            int oneBasedRow, oneBasedColumn;
            double entryValue = 1.0;

            if (isPatternMatrix) {
                if (!(entryStream >> oneBasedRow >> oneBasedColumn)) {
                    continue;
                }
                entryValue = 1.0;
            } else {
                if (!(entryStream >> oneBasedRow >> oneBasedColumn >> entryValue)) {
                    continue;
                }
            }

            // Convert to zero-based indexing
            int zeroBasedRow = oneBasedRow - 1;
            int zeroBasedColumn = oneBasedColumn - 1;

            if (zeroBasedRow < 0 || zeroBasedColumn < 0) {
                continue;
            }

            coordinateEntries.push_back({zeroBasedRow, zeroBasedColumn, entryValue});

            // Add symmetric entry if needed
            if (isSymmetricMatrix && zeroBasedRow != zeroBasedColumn) {
                coordinateEntries.push_back({zeroBasedColumn, zeroBasedRow, entryValue});
            }

            ++entryIndex;
        }
    }
};

// Forward declaration of GPU solver (from gpu_solver.cu)
extern "C" bool solve_dense_gpu(int n, const double* h_A_colmaj, const double* h_b, double* h_x, int nrhs, float* elapsed_ms_out);

// ============================================================================
// Utilities: convert COO to dense column-major, CPU solver, residuals, random b
// ============================================================================

static void coo_to_dense_colmaj(int nrows, int ncols, const vector<CoordinateEntry>& coo, vector<double>& A) {
    A.assign(size_t(nrows) * size_t(ncols), 0.0);
    int lda = nrows;
    for (const auto &e : coo) {
        if (e.row < 0 || e.column < 0 || e.row >= nrows || e.column >= ncols) continue;
        A[size_t(e.column) * size_t(lda) + size_t(e.row)] += e.value;
    }
}

// Simple CPU Gaussian elimination with partial pivoting (overwrites A and b)
static bool solve_dense_cpu_gauss(int n, vector<double>& A_colmaj, vector<double>& b, vector<double>& x) {
    if (n <= 0) return false;
    int lda = n;
    // Convert column-major to row-major temporary for easier pivoting, or operate in column-major
    // We'll work on column-major directly but index carefully: A[j*lda + i] is A(i,j)

    // Make copies (we'll overwrite)
    vector<double> aug(A_colmaj);
    vector<double> rhs(b);

    // Gaussian elimination with partial pivoting
    for (int k = 0; k < n; ++k) {
        // Find pivot row (max abs in column k from row k..n-1)
        double maxval = 0.0;
        int piv = -1;
        for (int i = k; i < n; ++i) {
            double v = fabs(aug[size_t(k) * size_t(lda) + size_t(i)]); // A(i,k)
            if (v > maxval) { maxval = v; piv = i; }
        }
        if (piv == -1 || maxval < 1e-15) {
            return false; // singular or zero pivot
        }
        if (piv != k) {
            // swap rows k and piv in aug (column-major storage)
            for (int j = 0; j < n; ++j) {
                std::swap(aug[size_t(j) * size_t(lda) + size_t(k)], aug[size_t(j) * size_t(lda) + size_t(piv)]);
            }
            std::swap(rhs[k], rhs[piv]);
        }

        // Eliminate rows below k
        double Akk = aug[size_t(k) * size_t(lda) + size_t(k)];
        if (fabs(Akk) < 1e-15) return false;
        for (int i = k + 1; i < n; ++i) {
            double Aik = aug[size_t(k) * size_t(lda) + size_t(i)];
            double mult = Aik / Akk;
            // row i = row i - mult * row k
            for (int j = k; j < n; ++j) {
                double Akj = aug[size_t(j) * size_t(lda) + size_t(k)]; // A(k,j) ??? need careful indexing
                // Wait: indexing is column-major: element (row=i, col=j) is aug[j*lda + i]
                // We want A(i,j) -= mult * A(k,j)
                aug[size_t(j) * size_t(lda) + size_t(i)] -= mult * aug[size_t(j) * size_t(lda) + size_t(k)];
            }
            rhs[i] -= mult * rhs[k];
        }
    }

    // Back substitution
    x.assign(n, 0.0);
    for (int i = n - 1; i >= 0; --i) {
        double sum = rhs[i];
        for (int j = i + 1; j < n; ++j) {
            sum -= aug[size_t(j) * size_t(lda) + size_t(i)] * x[j];
        }
        double Aii = aug[size_t(i) * size_t(lda) + size_t(i)];
        if (fabs(Aii) < 1e-15) return false;
        x[i] = sum / Aii;
    }
    return true;
}

static vector<double> generate_random_b(int n, unsigned int seed=12345) {
    vector<double> b(n);
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    for (int i = 0; i < n; ++i) b[i] = dist(rng);
    return b;
}

static double compute_residual_norm(int n, const vector<double>& A_colmaj, const vector<double>& x, const vector<double>& b) {
    int lda = n;
    vector<double> r(n, 0.0);
    for (int i = 0; i < n; ++i) {
        double s = 0.0;
        for (int j = 0; j < n; ++j) {
            s += A_colmaj[size_t(j) * size_t(lda) + size_t(i)] * x[j];
        }
        r[i] = s - b[i];
    }
    double norm = 0.0;
    for (int i = 0; i < n; ++i) norm += r[i] * r[i];
    return sqrt(norm);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        cout << "Usage: " << argv[0] << " <matrix.mtx> [--repeat N]" << endl;
        return 1;
    }
    string matrixPath = argv[1];
    int repeat = 5;
    for (int i = 2; i < argc; ++i) {
        string s = argv[i];
        if (s == "--repeat" && i + 1 < argc) { repeat = atoi(argv[++i]); }
    }

    int nrows = 0, ncols = 0;
    vector<CoordinateEntry> coo;
    if (!MatrixMarketReader::readMatrixMarketFile(matrixPath, nrows, ncols, coo)) {
        cerr << "Failed to read matrix: " << matrixPath << endl;
        return 1;
    }
    if (nrows != ncols) {
        cerr << "Matrix must be square for this solver" << endl;
        return 1;
    }
    int n = nrows;
    vector<double> A;
    coo_to_dense_colmaj(n, n, coo, A);

    // Generate random b
    vector<double> b = generate_random_b(n, 1337);

    // CPU solve
    vector<double> x_cpu;
    vector<double> A_copy = A; // gauss overwrites
    vector<double> b_copy = b;

    cout << "Running CPU solver (Gaussian elimination fallback) ..." << endl;
    auto t0 = chrono::high_resolution_clock::now();
    bool ok_cpu = solve_dense_cpu_gauss(n, A_copy, b_copy, x_cpu);
    auto t1 = chrono::high_resolution_clock::now();
    double cpu_ms = chrono::duration<double, milli>(t1 - t0).count();
    if (!ok_cpu) {
        cerr << "CPU solver failed (singular?)" << endl;
    } else {
        double res = compute_residual_norm(n, A, x_cpu, b);
        cout << "CPU time (ms): " << cpu_ms << ", residual norm: " << res << endl;
    }

    // GPU solve
    vector<double> x_gpu(n, 0.0);
    float gpu_ms = 0.0f;
    cout << "Running GPU solver (cuSOLVER) ..." << endl;
    bool ok_gpu = solve_dense_gpu(n, A.data(), b.data(), x_gpu.data(), 1, &gpu_ms);
    if (!ok_gpu) {
        cerr << "GPU solver returned failure" << endl;
    } else {
        double resg = compute_residual_norm(n, A, x_gpu, b);
        cout << "GPU time (ms): " << gpu_ms << ", residual norm: " << resg << endl;
    }

    return 0;
}