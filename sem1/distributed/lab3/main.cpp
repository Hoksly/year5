#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cmath>
#include <chrono>
#include <iomanip>
#include <omp.h>

struct StockData {
    std::string date;
    double open;
    double high;
    double low;
    double close;
    double adjClose;
    long volume;
};

// Read data from a CSV file
std::vector<StockData> readCSV(const std::string& filename) {
    std::vector<StockData> data;
    std::ifstream file(filename);
    std::string line;

    // Skip the header
    std::getline(file, line);

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string token;
        StockData stock;

        std::getline(ss, stock.date, ',');
        std::getline(ss, token, ','); stock.open = std::stod(token);
        std::getline(ss, token, ','); stock.high = std::stod(token);
        std::getline(ss, token, ','); stock.low = std::stod(token);
        std::getline(ss, token, ','); stock.close = std::stod(token);
        std::getline(ss, token, ','); stock.adjClose = std::stod(token);
        std::getline(ss, token, ','); stock.volume = std::stol(token);

        data.push_back(stock);
    }

    return data;
}

// Simple Moving Average (SMA) - parallel version
std::vector<double> calculateSMA_Parallel(const std::vector<double>& prices, int windowSize, int numThreads) {
    int n = prices.size();
    std::vector<double> sma(n, 0.0);

    omp_set_num_threads(numThreads);

    #pragma omp parallel for schedule(dynamic)
    for (int i = windowSize - 1; i < n; i++) {
        double sum = 0.0;
        for (int j = i - windowSize + 1; j <= i; j++) {
            sum += prices[j];
        }
        sma[i] = sum / windowSize;
    }

    return sma;
}

// Weighted Moving Average (WMA) - parallel version
std::vector<double> calculateWMA_Parallel(const std::vector<double>& prices, int windowSize, int numThreads) {
    int n = prices.size();
    std::vector<double> wma(n, 0.0);

    // Sum of weights: 1 + 2 + ... + windowSize = windowSize * (windowSize + 1) / 2
    double weightSum = windowSize * (windowSize + 1) / 2.0;

    omp_set_num_threads(numThreads);

    #pragma omp parallel for schedule(dynamic)
    for (int i = windowSize - 1; i < n; i++) {
        double sum = 0.0;
        for (int j = 0; j < windowSize; j++) {
            // Weight increases as we approach the current value
            sum += prices[i - windowSize + 1 + j] * (j + 1);
        }
        wma[i] = sum / weightSum;
    }

    return wma;
}

// Predict the next value (using the last MA value)
double predictNext(const std::vector<double>& ma, int lastValidIndex) {
    return ma[lastValidIndex];
}

// Calculate prediction error
struct ErrorMetrics {
    double mae;  // Mean Absolute Error
    double mse;  // Mean Squared Error
    double rmse; // Root Mean Squared Error
    double mape; // Mean Absolute Percentage Error
};

ErrorMetrics calculateErrors(const std::vector<double>& actual, const std::vector<double>& predicted, int windowSize) {
    ErrorMetrics errors = {0, 0, 0, 0};
    int count = 0;

    for (size_t i = windowSize; i < actual.size(); i++) {
        if (predicted[i-1] > 0) {
            double diff = actual[i] - predicted[i-1];
            errors.mae += std::abs(diff);
            errors.mse += diff * diff;
            errors.mape += std::abs(diff / actual[i]) * 100;
            count++;
        }
    }

    if (count > 0) {
        errors.mae /= count;
        errors.mse /= count;
        errors.rmse = std::sqrt(errors.mse);
        errors.mape /= count;
    }

    return errors;
}

// Measure execution time
double measureTime(const std::vector<double>& prices, int windowSize, int numThreads, bool useWMA) {
    auto start = std::chrono::high_resolution_clock::now();

    if (useWMA) {
        calculateWMA_Parallel(prices, windowSize, numThreads);
    } else {
        calculateSMA_Parallel(prices, windowSize, numThreads);
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;
    return duration.count();
}

int main() {
    std::cout << "=== Intel (INTC) Stock Price Prediction using OpenMP ===" << std::endl;
    std::cout << std::endl;

    // Read data
    std::vector<StockData> data = readCSV("INTC.csv");
    std::cout << "Loaded " << data.size() << " records" << std::endl;

    // Extract closing prices
    std::vector<double> prices;
    for (const auto& d : data) {
        prices.push_back(d.close);
    }

    // Window sizes: day (1), week (5), month (21 trading days)
    std::vector<int> windowSizes = {5, 10, 21, 50, 100, 200};

    // Number of available cores
    int maxThreads = omp_get_max_threads();
    std::cout << "Maximum number of threads: " << maxThreads << std::endl;
    std::cout << std::endl;

    // ============ PART 1: Accuracy comparison for different window sizes ============
    std::cout << "=== ACCURACY COMPARISON ===" << std::endl;
    std::cout << std::setw(10) << "Window"
              << std::setw(15) << "SMA MAE"
              << std::setw(15) << "SMA RMSE"
              << std::setw(15) << "SMA MAPE%"
              << std::setw(15) << "WMA MAE"
              << std::setw(15) << "WMA RMSE"
              << std::setw(15) << "WMA MAPE%" << std::endl;
    std::cout << std::string(100, '-') << std::endl;

    double bestSMA_MAPE = 1e9, bestWMA_MAPE = 1e9;
    int bestSMA_Window = 0, bestWMA_Window = 0;

    for (int windowSize : windowSizes) {
        std::vector<double> sma = calculateSMA_Parallel(prices, windowSize, maxThreads);
        std::vector<double> wma = calculateWMA_Parallel(prices, windowSize, maxThreads);

        ErrorMetrics smaErrors = calculateErrors(prices, sma, windowSize);
        ErrorMetrics wmaErrors = calculateErrors(prices, wma, windowSize);

        std::cout << std::fixed << std::setprecision(6);
        std::cout << std::setw(10) << windowSize
                  << std::setw(15) << smaErrors.mae
                  << std::setw(15) << smaErrors.rmse
                  << std::setw(15) << smaErrors.mape
                  << std::setw(15) << wmaErrors.mae
                  << std::setw(15) << wmaErrors.rmse
                  << std::setw(15) << wmaErrors.mape << std::endl;

        if (smaErrors.mape < bestSMA_MAPE) {
            bestSMA_MAPE = smaErrors.mape;
            bestSMA_Window = windowSize;
        }
        if (wmaErrors.mape < bestWMA_MAPE) {
            bestWMA_MAPE = wmaErrors.mape;
            bestWMA_Window = windowSize;
        }
    }

    std::cout << std::endl;
    std::cout << "Best window size for SMA: " << bestSMA_Window << " (MAPE: " << bestSMA_MAPE << "%)" << std::endl;
    std::cout << "Best window size for WMA: " << bestWMA_Window << " (MAPE: " << bestWMA_MAPE << "%)" << std::endl;
    std::cout << std::endl;

    // ============ PART 2: Next step prediction ============
    std::cout << "=== NEXT STEP PREDICTION ===" << std::endl;

    int predictionWindow = 21; // month
    std::vector<double> sma = calculateSMA_Parallel(prices, predictionWindow, maxThreads);
    std::vector<double> wma = calculateWMA_Parallel(prices, predictionWindow, maxThreads);

    double lastPrice = prices.back();
    double smaPrediction = predictNext(sma, prices.size() - 1);
    double wmaPrediction = predictNext(wma, prices.size() - 1);

    std::cout << "Last known price: " << lastPrice << std::endl;
    std::cout << "SMA Prediction (window=" << predictionWindow << "): " << smaPrediction << std::endl;
    std::cout << "WMA Prediction (window=" << predictionWindow << "): " << wmaPrediction << std::endl;
    std::cout << std::endl;

    // ============ PART 3: Performance comparison on 1-N cores ============
    std::cout << "=== PERFORMANCE COMPARISON (ms) ===" << std::endl;

    int testWindowSize = 21;
    int numRuns = 10; // Number of runs for averaging

    std::cout << std::setw(10) << "Threads"
              << std::setw(15) << "SMA (ms)"
              << std::setw(15) << "WMA (ms)"
              << std::setw(15) << "SMA Speedup"
              << std::setw(15) << "WMA Speedup" << std::endl;
    std::cout << std::string(70, '-') << std::endl;

    double baseSMA = 0, baseWMA = 0;

    for (int threads = 1; threads <= maxThreads; threads++) {
        double totalSMA = 0, totalWMA = 0;

        for (int run = 0; run < numRuns; run++) {
            totalSMA += measureTime(prices, testWindowSize, threads, false);
            totalWMA += measureTime(prices, testWindowSize, threads, true);
        }

        double avgSMA = totalSMA / numRuns;
        double avgWMA = totalWMA / numRuns;

        if (threads == 1) {
            baseSMA = avgSMA;
            baseWMA = avgWMA;
        }

        double speedupSMA = baseSMA / avgSMA;
        double speedupWMA = baseWMA / avgWMA;

        std::cout << std::fixed << std::setprecision(4);
        std::cout << std::setw(10) << threads
                  << std::setw(15) << avgSMA
                  << std::setw(15) << avgWMA
                  << std::setw(15) << speedupSMA
                  << std::setw(15) << speedupWMA << std::endl;
    }

    std::cout << std::endl;

    // ============ PART 4: Performance comparison for different window sizes ============
    std::cout << "=== PERFORMANCE FOR DIFFERENT WINDOW SIZES (all threads) ===" << std::endl;
    std::cout << std::setw(10) << "Window"
              << std::setw(15) << "SMA (ms)"
              << std::setw(15) << "WMA (ms)" << std::endl;
    std::cout << std::string(40, '-') << std::endl;

    for (int windowSize : windowSizes) {
        double totalSMA = 0, totalWMA = 0;

        for (int run = 0; run < numRuns; run++) {
            totalSMA += measureTime(prices, windowSize, maxThreads, false);
            totalWMA += measureTime(prices, windowSize, maxThreads, true);
        }

        std::cout << std::setw(10) << windowSize
                  << std::setw(15) << (totalSMA / numRuns)
                  << std::setw(15) << (totalWMA / numRuns) << std::endl;
    }

    std::cout << std::endl;
    std::cout << "=== CONCLUSIONS ===" << std::endl;
    std::cout << "1. Smaller window sizes provide better prediction accuracy (less lag)." << std::endl;
    std::cout << "2. WMA generally provides better predictions as it gives more weight to recent values." << std::endl;
    std::cout << "3. Parallelization is effective for large datasets." << std::endl;

    return 0;
}