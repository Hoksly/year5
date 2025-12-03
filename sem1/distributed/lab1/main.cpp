#include <mpi.h>
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

/**
 * @brief Compressed Sparse Row (CSR) format for efficient sparse matrix storage
 */
struct CompressedSparseRowMatrix {
    int numberOfRows;
    int numberOfColumns;
    vector<int> rowPointers;    // Size: numberOfRows + 1
    vector<int> columnIndices;  // Size: numberOfNonZeros
    vector<double> values;      // Size: numberOfNonZeros

    CompressedSparseRowMatrix()
        : numberOfRows(0), numberOfColumns(0) {}

    int getNumberOfNonZeros() const {
        return static_cast<int>(values.size());
    }
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

// ============================================================================
// Sparse Matrix Format Converter
// ============================================================================

/**
 * @brief Converts between sparse matrix formats
 */
class SparseMatrixConverter {
public:
    /**
     * @brief Convert COO format to CSR format, combining duplicate entries
     */
    static CompressedSparseRowMatrix convertCOOtoCSR(
        int numberOfRows,
        int numberOfColumns,
        vector<CoordinateEntry>& coordinateEntries
    ) {
        CompressedSparseRowMatrix csrMatrix;
        csrMatrix.numberOfRows = numberOfRows;
        csrMatrix.numberOfColumns = numberOfColumns;

        if (coordinateEntries.empty()) {
            csrMatrix.rowPointers.assign(numberOfRows + 1, 0);
            return csrMatrix;
        }

        // Sort entries by row, then by column
        sort(coordinateEntries.begin(), coordinateEntries.end(),
             [](const CoordinateEntry& a, const CoordinateEntry& b) {
                 if (a.row != b.row) return a.row < b.row;
                 return a.column < b.column;
             });

        // Combine duplicates and build CSR structure
        vector<int> rowPointers(numberOfRows + 1, 0);
        vector<int> columnIndices;
        vector<double> values;

        size_t entryIndex = 0;
        while (entryIndex < coordinateEntries.size()) {
            int currentRow = coordinateEntries[entryIndex].row;

            // Process all entries in current row
            while (entryIndex < coordinateEntries.size() &&
                   coordinateEntries[entryIndex].row == currentRow) {
                int currentColumn = coordinateEntries[entryIndex].column;
                double accumulatedValue = coordinateEntries[entryIndex].value;
                ++entryIndex;

                // Accumulate duplicate entries
                while (entryIndex < coordinateEntries.size() &&
                       coordinateEntries[entryIndex].row == currentRow &&
                       coordinateEntries[entryIndex].column == currentColumn) {
                    accumulatedValue += coordinateEntries[entryIndex].value;
                    ++entryIndex;
                }

                columnIndices.push_back(currentColumn);
                values.push_back(accumulatedValue);
                rowPointers[currentRow + 1]++;
            }
        }

        // Convert row counts to cumulative pointers
        for (int rowIndex = 1; rowIndex <= numberOfRows; ++rowIndex) {
            rowPointers[rowIndex] += rowPointers[rowIndex - 1];
        }

        csrMatrix.rowPointers.swap(rowPointers);
        csrMatrix.columnIndices.swap(columnIndices);
        csrMatrix.values.swap(values);

        return csrMatrix;
    }

    /**
     * @brief Convert COO to CSR for a specific row range (for distributed matrices)
     */
    static CompressedSparseRowMatrix convertCOOtoCSRLocal(
        int globalNumberOfRows,
        int globalNumberOfColumns,
        vector<CoordinateEntry>& localCoordinateEntries,
        int localRowStart,
        int localRowEnd
    ) {
        int localNumberOfRows = localRowEnd - localRowStart;
        CompressedSparseRowMatrix csrMatrix;
        csrMatrix.numberOfRows = localNumberOfRows;
        csrMatrix.numberOfColumns = globalNumberOfColumns;

        if (localCoordinateEntries.empty()) {
            csrMatrix.rowPointers.assign(localNumberOfRows + 1, 0);
            return csrMatrix;
        }

        // Sort entries
        sort(localCoordinateEntries.begin(), localCoordinateEntries.end(),
             [](const CoordinateEntry& a, const CoordinateEntry& b) {
                 if (a.row != b.row) return a.row < b.row;
                 return a.column < b.column;
             });

        vector<int> rowPointers(localNumberOfRows + 1, 0);
        vector<int> columnIndices;
        vector<double> values;

        size_t entryIndex = 0;
        while (entryIndex < localCoordinateEntries.size()) {
            int localRow = localCoordinateEntries[entryIndex].row - localRowStart;

            if (localRow < 0 || localRow >= localNumberOfRows) {
                ++entryIndex;
                continue;
            }

            while (entryIndex < localCoordinateEntries.size() &&
                   (localCoordinateEntries[entryIndex].row - localRowStart) == localRow) {
                int currentColumn = localCoordinateEntries[entryIndex].column;
                double accumulatedValue = localCoordinateEntries[entryIndex].value;
                ++entryIndex;

                while (entryIndex < localCoordinateEntries.size() &&
                       (localCoordinateEntries[entryIndex].row - localRowStart) == localRow &&
                       localCoordinateEntries[entryIndex].column == currentColumn) {
                    accumulatedValue += localCoordinateEntries[entryIndex].value;
                    ++entryIndex;
                }

                columnIndices.push_back(currentColumn);
                values.push_back(accumulatedValue);
                rowPointers[localRow + 1]++;
            }
        }

        for (int rowIndex = 1; rowIndex <= localNumberOfRows; ++rowIndex) {
            rowPointers[rowIndex] += rowPointers[rowIndex - 1];
        }

        csrMatrix.rowPointers.swap(rowPointers);
        csrMatrix.columnIndices.swap(columnIndices);
        csrMatrix.values.swap(values);

        return csrMatrix;
    }
};

// ============================================================================
// Sparse Matrix-Vector Multiplication Engine
// ============================================================================

/**
 * @brief Handles sparse matrix-vector multiplication with MPI distribution
 */
class DistributedSparseMatrixVectorMultiplier {
private:
    int mpiRank;
    int mpiSize;
    MPI_Comm mpiCommunicator;

public:
    DistributedSparseMatrixVectorMultiplier(MPI_Comm communicator = MPI_COMM_WORLD)
        : mpiCommunicator(communicator) {
        MPI_Comm_rank(mpiCommunicator, &mpiRank);
        MPI_Comm_size(mpiCommunicator, &mpiSize);
    }

    /**
     * @brief Perform distributed sparse matrix-vector multiplication: y = A * x
     * @param localMatrix Local portion of matrix A in CSR format
     * @param globalVector Vector x (must be complete on all processes)
     * @return Local portion of result vector y
     */
    vector<double> multiply(
        const CompressedSparseRowMatrix& localMatrix,
        const vector<double>& globalVector
    ) const {
        int localNumberOfRows = localMatrix.numberOfRows;
        vector<double> localResult(localNumberOfRows, 0.0);

        // Compute local matrix-vector product
        for (int localRowIndex = 0; localRowIndex < localNumberOfRows; ++localRowIndex) {
            double rowDotProduct = 0.0;

            int rowStart = localMatrix.rowPointers[localRowIndex];
            int rowEnd = localMatrix.rowPointers[localRowIndex + 1];

            for (int entryIndex = rowStart; entryIndex < rowEnd; ++entryIndex) {
                int columnIndex = localMatrix.columnIndices[entryIndex];
                double matrixValue = localMatrix.values[entryIndex];

                if (columnIndex >= 0 &&
                    columnIndex < static_cast<int>(globalVector.size())) {
                    rowDotProduct += matrixValue * globalVector[columnIndex];
                }
            }

            localResult[localRowIndex] = rowDotProduct;
        }

        return localResult;
    }

    /**
     * @brief Calculate row distribution across MPI processes
     */
    vector<int> calculateRowDistribution(int totalNumberOfRows) const {
        vector<int> rowStartIndices(mpiSize + 1, 0);

        int baseRowsPerProcess = totalNumberOfRows / mpiSize;
        int remainingRows = totalNumberOfRows % mpiSize;

        for (int processRank = 0; processRank < mpiSize; ++processRank) {
            rowStartIndices[processRank] =
                processRank * baseRowsPerProcess + min(processRank, remainingRows);
        }
        rowStartIndices[mpiSize] = totalNumberOfRows;

        return rowStartIndices;
    }

    /**
     * @brief Distribute matrix rows to appropriate processes
     */
    vector<CoordinateEntry> distributeMatrixRows(
        const vector<CoordinateEntry>& allEntries,
        const vector<int>& rowDistribution,
        int localRowStart,
        int localRowEnd
    ) {
        vector<CoordinateEntry> localEntries;

        if (mpiRank == 0) {
            // Root process distributes matrix entries
            vector<vector<CoordinateEntry>> entriesPerProcess(mpiSize);

            for (const auto& entry : allEntries) {
                int ownerProcess = findOwnerProcess(entry.row, rowDistribution);
                entriesPerProcess[ownerProcess].push_back(entry);
            }

            // Keep local entries
            localEntries.swap(entriesPerProcess[0]);

            // Send to other processes
            for (int destinationRank = 1; destinationRank < mpiSize; ++destinationRank) {
                sendCoordinateEntries(entriesPerProcess[destinationRank], destinationRank);
            }
        } else {
            // Non-root processes receive their entries
            localEntries = receiveCoordinateEntries();
        }

        return localEntries;
    }

    /**
     * @brief Gather local results to root process
     */
    vector<double> gatherResults(const vector<double>& localResult) const {
        int localSize = static_cast<int>(localResult.size());
        vector<int> allSizes(mpiSize);

        MPI_Gather(&localSize, 1, MPI_INT,
                   allSizes.data(), 1, MPI_INT,
                   0, mpiCommunicator);

        vector<int> displacements(mpiSize, 0);
        int totalSize = 0;

        if (mpiRank == 0) {
            for (int processRank = 0; processRank < mpiSize; ++processRank) {
                displacements[processRank] = totalSize;
                totalSize += allSizes[processRank];
            }
        }

        vector<double> globalResult(totalSize);

        MPI_Gatherv(localResult.data(), localSize, MPI_DOUBLE,
                    globalResult.data(), allSizes.data(),
                    displacements.data(), MPI_DOUBLE,
                    0, mpiCommunicator);

        return globalResult;
    }

private:
    /**
     * @brief Find which process owns a given row
     */
    int findOwnerProcess(int rowIndex, const vector<int>& rowDistribution) const {
        int ownerRank = static_cast<int>(
            upper_bound(rowDistribution.begin(), rowDistribution.end(), rowIndex) -
            rowDistribution.begin() - 1
        );

        return max(0, min(ownerRank, mpiSize - 1));
    }

    /**
     * @brief Send coordinate entries to another process
     */
    void sendCoordinateEntries(
        const vector<CoordinateEntry>& entries,
        int destinationRank
    ) const {
        int entryCount = static_cast<int>(entries.size());
        MPI_Send(&entryCount, 1, MPI_INT, destinationRank, 0, mpiCommunicator);

        if (entryCount > 0) {
            vector<int> rows(entryCount), columns(entryCount);
            vector<double> values(entryCount);

            for (int i = 0; i < entryCount; ++i) {
                rows[i] = entries[i].row;
                columns[i] = entries[i].column;
                values[i] = entries[i].value;
            }

            MPI_Send(rows.data(), entryCount, MPI_INT,
                    destinationRank, 1, mpiCommunicator);
            MPI_Send(columns.data(), entryCount, MPI_INT,
                    destinationRank, 2, mpiCommunicator);
            MPI_Send(values.data(), entryCount, MPI_DOUBLE,
                    destinationRank, 3, mpiCommunicator);
        }
    }

    /**
     * @brief Receive coordinate entries from root process
     */
    vector<CoordinateEntry> receiveCoordinateEntries() const {
        int entryCount = 0;
        MPI_Recv(&entryCount, 1, MPI_INT, 0, 0,
                mpiCommunicator, MPI_STATUS_IGNORE);

        vector<CoordinateEntry> entries;

        if (entryCount > 0) {
            vector<int> rows(entryCount), columns(entryCount);
            vector<double> values(entryCount);

            MPI_Recv(rows.data(), entryCount, MPI_INT, 0, 1,
                    mpiCommunicator, MPI_STATUS_IGNORE);
            MPI_Recv(columns.data(), entryCount, MPI_INT, 0, 2,
                    mpiCommunicator, MPI_STATUS_IGNORE);
            MPI_Recv(values.data(), entryCount, MPI_DOUBLE, 0, 3,
                    mpiCommunicator, MPI_STATUS_IGNORE);

            entries.resize(entryCount);
            for (int i = 0; i < entryCount; ++i) {
                entries[i] = {rows[i], columns[i], values[i]};
            }
        }

        return entries;
    }
};

// ============================================================================
// Matrix Market Writer
// ============================================================================

/**
 * @brief Writes results in Matrix Market format
 */
class MatrixMarketWriter {
public:
    /**
     * @brief Write a dense vector to Matrix Market coordinate format
     */
    static bool writeVector(
        const string& outputPath,
        const vector<double>& vectorData,
        double zeroTolerance = 1e-12
    ) {
        // Collect non-zero entries
        vector<pair<int, double>> nonZeroEntries;
        nonZeroEntries.reserve(vectorData.size());

        for (size_t i = 0; i < vectorData.size(); ++i) {
            if (fabs(vectorData[i]) > zeroTolerance) {
                nonZeroEntries.push_back({static_cast<int>(i), vectorData[i]});
            }
        }

        // Write to file
        ofstream outputFile(outputPath);
        if (!outputFile) {
            return false;
        }

        outputFile << "%%MatrixMarket matrix coordinate real general\n";
        outputFile << vectorData.size() << " " << 1 << " "
                  << nonZeroEntries.size() << "\n";
        outputFile << setprecision(12);

        for (const auto& entry : nonZeroEntries) {
            outputFile << (entry.first + 1) << " " << 1 << " "
                      << entry.second << "\n";
        }

        outputFile.close();
        return true;
    }
};

// ============================================================================
// Main Application
// ============================================================================

/**
 * @brief Main application orchestrating the distributed SpMV operation
 */
class DistributedSpMVApplication {
private:
    int mpiRank;
    int mpiSize;
    string matrixFilePath;
    string vectorFilePath;
    string outputFilePath;
    double zeroTolerance;

public:
    DistributedSpMVApplication(int argc, char** argv) {
        MPI_Init(&argc, &argv);
        MPI_Comm_rank(MPI_COMM_WORLD, &mpiRank);
        MPI_Comm_size(MPI_COMM_WORLD, &mpiSize);

        if (!parseCommandLineArguments(argc, argv)) {
            if (mpiRank == 0) {
                printUsage(argv[0]);
            }
            MPI_Finalize();
            exit(1);
        }
    }

    ~DistributedSpMVApplication() {
        MPI_Finalize();
    }

    /**
     * @brief Execute the distributed sparse matrix-vector multiplication
     */
    int run() {
        // Step 1: Read and validate inputs on root
        int matrixRows = 0, matrixColumns = 0;
        int vectorRows = 0, vectorColumns = 0;
        vector<CoordinateEntry> matrixEntries, vectorEntries;

        if (!readAndValidateInputs(matrixRows, matrixColumns,
                                   vectorRows, vectorColumns,
                                   matrixEntries, vectorEntries)) {
            return 1;
        }

        // Step 2: Broadcast dimensions
        broadcastDimensions(matrixRows, matrixColumns, vectorRows, vectorColumns);

        // Step 3: Distribute matrix across processes
        DistributedSparseMatrixVectorMultiplier multiplier;
        vector<int> rowDistribution = multiplier.calculateRowDistribution(matrixRows);

        int localRowStart = rowDistribution[mpiRank];
        int localRowEnd = rowDistribution[mpiRank + 1];

        vector<CoordinateEntry> localMatrixEntries =
            multiplier.distributeMatrixRows(matrixEntries, rowDistribution,
                                           localRowStart, localRowEnd);

        // Free memory on root
        matrixEntries.clear();
        matrixEntries.shrink_to_fit();

        // Step 4: Convert to CSR format
        CompressedSparseRowMatrix localMatrix =
            SparseMatrixConverter::convertCOOtoCSRLocal(
                matrixRows, matrixColumns, localMatrixEntries,
                localRowStart, localRowEnd
            );

        localMatrixEntries.clear();
        localMatrixEntries.shrink_to_fit();

        // Step 5: Prepare and broadcast vector
        vector<double> denseVector = prepareDenseVector(
            vectorRows, vectorColumns, vectorEntries
        );

        vectorEntries.clear();
        vectorEntries.shrink_to_fit();

        // Step 6: Perform local multiplication
        vector<double> localResult = multiplier.multiply(localMatrix, denseVector);

        // Step 7: Gather results
        vector<double> globalResult = multiplier.gatherResults(localResult);

        // Step 8: Write output
        if (mpiRank == 0) {
            if (MatrixMarketWriter::writeVector(outputFilePath, globalResult,
                                               zeroTolerance)) {
                cerr << "Successfully wrote output: " << outputFilePath
                     << " (nnz=" << countNonZeros(globalResult) << ")\n";
            } else {
                cerr << "Failed to write output file: " << outputFilePath << endl;
                return 1;
            }
        }

        return 0;
    }

private:
    /**
     * @brief Parse command line arguments
     */
    bool parseCommandLineArguments(int argc, char** argv) {
        if (argc < 4) {
            return false;
        }

        matrixFilePath = argv[1];
        vectorFilePath = argv[2];
        outputFilePath = argv[3];
        zeroTolerance = (argc >= 5) ? atof(argv[4]) : 1e-12;

        return true;
    }

    /**
     * @brief Print usage information
     */
    void printUsage(const char* programName) const {
        cerr << "Usage: " << programName
             << " A.mtx x.mtx out.mtx [tolerance]\n";
        cerr << "  A.mtx       : Input matrix file in Matrix Market format\n";
        cerr << "  x.mtx       : Input vector file in Matrix Market format\n";
        cerr << "  out.mtx     : Output file path\n";
        cerr << "  tolerance   : Zero tolerance (default: 1e-12)\n";
    }

    /**
     * @brief Read and validate input files on root process
     */
    bool readAndValidateInputs(
        int& matrixRows, int& matrixColumns,
        int& vectorRows, int& vectorColumns,
        vector<CoordinateEntry>& matrixEntries,
        vector<CoordinateEntry>& vectorEntries
    ) {
        int validationStatus = 1;

        if (mpiRank == 0) {
            if (!MatrixMarketReader::readMatrixMarketFile(
                    matrixFilePath, matrixRows, matrixColumns, matrixEntries)) {
                cerr << "Failed to read matrix file: " << matrixFilePath << endl;
                validationStatus = 0;
            }

            if (validationStatus && !MatrixMarketReader::readMatrixMarketFile(
                    vectorFilePath, vectorRows, vectorColumns, vectorEntries)) {
                cerr << "Failed to read vector file: " << vectorFilePath << endl;
                validationStatus = 0;
            }

            if (validationStatus) {
                if (!validateVectorDimensions(vectorRows, vectorColumns, matrixColumns)) {
                    validationStatus = 0;
                }
            }
        }

        MPI_Bcast(&validationStatus, 1, MPI_INT, 0, MPI_COMM_WORLD);

        if (!validationStatus) {
            if (mpiRank == 0) {
                cerr << "Input validation failed. Exiting.\n";
            }
            return false;
        }

        return true;
    }

    /**
     * @brief Validate vector dimensions against matrix
     */
    bool validateVectorDimensions(
        int vectorRows, int vectorColumns, int matrixColumns
    ) const {
        int vectorLength = 0;
        bool isColumnVector = false;

        if (vectorColumns == 1) {
            vectorLength = vectorRows;
            isColumnVector = true;
        } else if (vectorRows == 1) {
            vectorLength = vectorColumns;
            isColumnVector = false;
        } else {
            cerr << "Second input must be a vector (one row or one column). "
                 << "Got dimensions: " << vectorRows << " x " << vectorColumns << "\n";
            return false;
        }

        if (matrixColumns != vectorLength) {
            cerr << "Dimension mismatch: matrix columns = " << matrixColumns
                 << ", vector length = " << vectorLength << "\n";
            return false;
        }

        return true;
    }

    /**
     * @brief Broadcast matrix and vector dimensions to all processes
     */
    void broadcastDimensions(
        int& matrixRows, int& matrixColumns,
        int& vectorRows, int& vectorColumns
    ) const {
        MPI_Bcast(&matrixRows, 1, MPI_INT, 0, MPI_COMM_WORLD);
        MPI_Bcast(&matrixColumns, 1, MPI_INT, 0, MPI_COMM_WORLD);
        MPI_Bcast(&vectorRows, 1, MPI_INT, 0, MPI_COMM_WORLD);
        MPI_Bcast(&vectorColumns, 1, MPI_INT, 0, MPI_COMM_WORLD);
    }

    /**
     * @brief Convert sparse vector to dense format and broadcast
     */
    vector<double> prepareDenseVector(
        int vectorRows, int vectorColumns,
        vector<CoordinateEntry>& vectorEntries
    ) const {
        int vectorLength = 0;
        vector<double> denseVector;

        if (mpiRank == 0) {
            vectorLength = (vectorColumns == 1) ? vectorRows : vectorColumns;
            denseVector.assign(vectorLength, 0.0);

            // Accumulate vector values (handle duplicates)
            for (const auto& entry : vectorEntries) {
                int index = (vectorColumns == 1) ? entry.row : entry.column;
                if (index >= 0 && index < vectorLength) {
                    denseVector[index] += entry.value;
                }
            }
        }

        // Broadcast vector length and data to all processes
        MPI_Bcast(&vectorLength, 1, MPI_INT, 0, MPI_COMM_WORLD);

        if (mpiRank != 0) {
            denseVector.assign(vectorLength, 0.0);
        }

        if (vectorLength > 0) {
            MPI_Bcast(denseVector.data(), vectorLength, MPI_DOUBLE,
                     0, MPI_COMM_WORLD);
        }

        return denseVector;
    }

    /**
     * @brief Count non-zero entries in result vector
     */
    int countNonZeros(const vector<double>& vectorData) const {
        int count = 0;
        for (double value : vectorData) {
            if (fabs(value) > zeroTolerance) {
                ++count;
            }
        }
        return count;
    }
};

// ============================================================================
// Program Entry Point
// ============================================================================

int main(int argc, char** argv) {
    try {
        DistributedSpMVApplication application(argc, argv);
        return application.run();
    } catch (const exception& e) {
        cerr << "Error: " << e.what() << endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    } catch (...) {
        cerr << "Unknown error occurred" << endl;
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
}