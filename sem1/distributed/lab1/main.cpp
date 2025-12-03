#include <mpi.h>
#include <bits/stdc++.h>
using namespace std;

struct COO { int r, c; double v; };

struct CSR {
    int nrows = 0;
    int ncols = 0;
    vector<int> row_ptr; // size nrows+1
    vector<int> col_idx; // size nnz
    vector<double> vals; // size nnz
};

// Read Matrix Market coordinate (supports 'pattern' or 'real' and 'symmetric' or 'general')
bool read_matrix_market(const string &path, int &nrows, int &ncols, vector<COO> &coo) {
    ifstream in(path);
    if(!in) return false;
    string line;
    // header
    if(!getline(in, line)) return false;
    if(line.size() < 2 || line[0] != '%') {
        // still could be fine; MatrixMarket often starts with %%MatrixMarket
    }
    bool coordinate = false;
    bool pattern = false;
    bool real = false;
    bool symmetric = false;
    // parse header tokens
    {
        string header = line;
        // If first token is '%%MatrixMarket' parse the rest
        stringstream ss(header);
        string token;
        ss >> token; // possibly %%MatrixMarket
        if(token == "%%MatrixMarket") {
            string type, format, field, symmetry;
            if(!(ss >> type >> format >> field >> symmetry)) {
                // header might extend to next tokens in next lines; we'll try to parse more from file if needed
                // fallback: read rest of header from first non-comment lines
            } else {
                coordinate = (format == "coordinate");
                pattern = (field == "pattern");
                real = (field == "real" || field == "integer");
                if(symmetry == "symmetric" || symmetry == "hermitian") symmetric = true;
            }
        } else {
            // Not standard header — try to detect later
        }
    }
    // skip comments
    while(getline(in, line)){
        if(line.size() == 0) continue;
        if(line[0] == '%') continue;
        // this line should contain dimensions
        stringstream ss(line);
        int m,n,nnz;
        if(!(ss >> m >> n >> nnz)) {
            continue; // skip weird lines
        }
        nrows = m; ncols = n;
        coo.clear(); coo.reserve(max(0, nnz));
        // now read nnz entries
        for(int k=0;k<nnz;){
            if(!getline(in, line)) break;
            if(line.size() == 0) continue;
            if(line[0] == '%') continue;
            stringstream es(line);
            int i,j; double val = 1.0;
            if(pattern) {
                if(!(es >> i >> j)) continue;
                val = 1.0;
            } else {
                if(!(es >> i >> j >> val)) continue;
            }
            // convert to 0-based
            int r = i-1;
            int c = j-1;
            if(r < 0 || c < 0) continue;
            coo.push_back({r,c,val});
            if(symmetric && r != c) {
                coo.push_back({c,r,val});
            }
            // we advanced to 1 or 2 actual entries depending on symmetric; count only original nnz
            ++k;
        }
        return true;
    }
    return false;
}

// Convert COO to CSR (sums duplicates)
CSR coo_to_csr(int nrows, int ncols, vector<COO> &coo) {
    CSR A;
    A.nrows = nrows; A.ncols = ncols;
    if(coo.empty()) {
        A.row_ptr.assign(nrows+1, 0);
        return A;
    }
    // sort by (r,c)
    sort(coo.begin(), coo.end(), [](const COO &a, const COO &b){ if(a.r!=b.r) return a.r < b.r; return a.c < b.c; });
    // combine duplicates
    vector<int> row_ptr(nrows+1, 0);
    vector<int> cols;
    vector<double> vals;
    int idx = 0;
    while(idx < (int)coo.size()){
        int r = coo[idx].r;
        // process this row
        while(idx < (int)coo.size() && coo[idx].r == r) {
            int c = coo[idx].c;
            double s = coo[idx].v;
            ++idx;
            while(idx < (int)coo.size() && coo[idx].r == r && coo[idx].c == c) {
                s += coo[idx].v; ++idx;
            }
            cols.push_back(c);
            vals.push_back(s);
            row_ptr[r+1]++;
        }
    }
    // convert row counts to pointers
    for(int i=1;i<=nrows;++i) row_ptr[i] += row_ptr[i-1];
    A.row_ptr.swap(row_ptr);
    A.col_idx.swap(cols);
    A.vals.swap(vals);
    return A;
}

// Convert vector<COO> to CSR but only include rows in [rstart, rend) and shift rows to local indexing
CSR coo_to_csr_local(int nrows_global, int ncols_global, vector<COO> &coo_local, int rstart, int rend) {
    int local_nrows = rend - rstart;
    CSR A;
    A.nrows = local_nrows; A.ncols = ncols_global;
    if(coo_local.empty()){
        A.row_ptr.assign(local_nrows+1, 0);
        return A;
    }
    // sort
    sort(coo_local.begin(), coo_local.end(), [](const COO &a, const COO &b){ if(a.r!=b.r) return a.r < b.r; return a.c < b.c; });
    vector<int> row_ptr(local_nrows+1, 0);
    vector<int> cols;
    vector<double> vals;
    int idx = 0;
    while(idx < (int)coo_local.size()){
        int r = coo_local[idx].r - rstart; // local row index
        if(r < 0 || r >= local_nrows) { ++idx; continue; }
        while(idx < (int)coo_local.size() && (coo_local[idx].r - rstart) == r) {
            int c = coo_local[idx].c;
            double s = coo_local[idx].v;
            ++idx;
            while(idx < (int)coo_local.size() && (coo_local[idx].r - rstart) == r && coo_local[idx].c == c) {
                s += coo_local[idx].v; ++idx;
            }
            cols.push_back(c);
            vals.push_back(s);
            row_ptr[r+1]++;
        }
    }
    for(int i=1;i<=local_nrows;++i) row_ptr[i] += row_ptr[i-1];
    A.row_ptr.swap(row_ptr);
    A.col_idx.swap(cols);
    A.vals.swap(vals);
    return A;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if(argc < 4) {
        if(rank == 0) {
            cerr << "Usage: " << argv[0] << " A.mtx x.mtx out.mtx [tol]" << endl;
        }
        MPI_Finalize();
        return 1;
    }
    string Apath = argv[1];
    string XPath = argv[2];
    string OutPath = argv[3];
    double tol = 1e-12;
    if(argc >= 5) tol = atof(argv[4]);

    int A_nrows=0, A_ncols=0, x_nrows=0, x_ncols=0;
    vector<COO> A_coo_all, x_coo_all;

    // Rank 0 reads files and validates inputs; then broadcast an 'ok' flag to all ranks
    int ok = 1; // 1 = inputs valid, 0 = invalid
    if(rank == 0) {
        if(!read_matrix_market(Apath, A_nrows, A_ncols, A_coo_all)) {
            cerr << "Failed to read A file: " << Apath << endl;
            ok = 0;
        }
        if(ok && !read_matrix_market(XPath, x_nrows, x_ncols, x_coo_all)) {
            cerr << "Failed to read x file: " << XPath << endl;
            ok = 0;
        }
        if(ok) {
            // Determine vector length and orientation
            int x_len = 0;
            bool x_is_col = false;
            if(x_ncols == 1) { x_len = x_nrows; x_is_col = true; }
            else if(x_nrows == 1) { x_len = x_ncols; x_is_col = false; }
            else {
                cerr << "Second input must be a vector (one column or one row). Got dimensions: " << x_nrows << " x " << x_ncols << "\n";
                ok = 0;
            }
            if(ok && A_ncols != x_len) {
                cerr << "Inner dimensions mismatch: A.cols="<<A_ncols<<" x.len="<<x_len<<"\n";
                ok = 0;
            }
        }
    }

    // Broadcast whether inputs are valid
    MPI_Bcast(&ok, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if(!ok) {
        if(rank == 0) cerr << "Input validation failed. Exiting." << endl;
        MPI_Finalize();
        return 1;
    }

    // Broadcast matrix sizes (safe now because inputs validated and read on rank 0)
    MPI_Bcast(&A_nrows, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&A_ncols, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&x_nrows, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&x_ncols, 1, MPI_INT, 0, MPI_COMM_WORLD);

    // Partition rows of A across ranks (contiguous blocks)
    vector<int> row_starts(size+1,0);
    int base = A_nrows / size;
    int rem = A_nrows % size;
    for(int r=0;r<size;++r){
        row_starts[r] = r*base + min(r, rem);
    }
    row_starts[size] = A_nrows;
    int rstart = row_starts[rank];
    int rend = row_starts[rank+1];
    int local_nrows = rend - rstart;

    // Distribute A: send COO entries whose row in [rstart, rend) to each rank
    vector<COO> A_coo_local;
    if(rank == 0) {
        // For each rank prepare a vector of entries
        vector<vector<COO>> sendbuf(size);
        for(const auto &e : A_coo_all){
            int r = e.r;
            int owner = upper_bound(row_starts.begin(), row_starts.end(), r) - row_starts.begin() - 1;
            if(owner < 0) owner = 0;
            if(owner >= size) owner = size-1;
            sendbuf[owner].push_back(e);
        }
        // rank 0 keeps its portion
        A_coo_local.swap(sendbuf[0]);
        // send others
        for(int dest=1; dest<size; ++dest){
            int cnt = (int)sendbuf[dest].size();
            MPI_Send(&cnt, 1, MPI_INT, dest, 0, MPI_COMM_WORLD);
            if(cnt > 0){
                // prepare arrays
                vector<int> rows(cnt), cols(cnt);
                vector<double> vals(cnt);
                for(int i=0;i<cnt;++i){ rows[i] = sendbuf[dest][i].r; cols[i] = sendbuf[dest][i].c; vals[i] = sendbuf[dest][i].v; }
                MPI_Send(rows.data(), cnt, MPI_INT, dest, 1, MPI_COMM_WORLD);
                MPI_Send(cols.data(), cnt, MPI_INT, dest, 2, MPI_COMM_WORLD);
                MPI_Send(vals.data(), cnt, MPI_DOUBLE, dest, 3, MPI_COMM_WORLD);
            }
        }
    } else {
        int cnt=0;
        MPI_Recv(&cnt, 1, MPI_INT, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        if(cnt > 0){
            vector<int> rows(cnt), cols(cnt);
            vector<double> vals(cnt);
            MPI_Recv(rows.data(), cnt, MPI_INT, 0, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Recv(cols.data(), cnt, MPI_INT, 0, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Recv(vals.data(), cnt, MPI_DOUBLE, 0, 3, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            A_coo_local.resize(cnt);
            for(int i=0;i<cnt;++i){ A_coo_local[i] = {rows[i], cols[i], vals[i]}; }
        }
    }

    // Convert local A COO to local CSR
    CSR A_local = coo_to_csr_local(A_nrows, A_ncols, A_coo_local, rstart, rend);

    // Prepare dense vector x on root and broadcast
    int x_len = 0;
    vector<double> x_dense;
    if(rank == 0){
        if(x_ncols == 1) x_len = x_nrows; else x_len = x_ncols; // validated earlier
        x_dense.assign(x_len, 0.0);
        // sum duplicates
        for(const auto &e : x_coo_all){
            int idx = (x_ncols == 1) ? e.r : e.c;
            if(idx >=0 && idx < x_len) x_dense[idx] += e.v;
        }
    }
    // broadcast vector length then values
    MPI_Bcast(&x_len, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if(rank != 0) x_dense.assign(x_len, 0.0);
    if(x_len > 0) MPI_Bcast(x_dense.data(), x_len, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    // Free large local buffers
    A_coo_all.clear(); A_coo_all.shrink_to_fit(); x_coo_all.clear(); x_coo_all.shrink_to_fit(); A_coo_local.clear(); A_coo_local.shrink_to_fit();

    // Local multiplication: for each local row, compute dot-product with x
    vector<double> y_local(local_nrows, 0.0);
    for(int lr=0; lr < A_local.nrows; ++lr){
        double s = 0.0;
        int a_start = A_local.row_ptr[lr];
        int a_end = A_local.row_ptr[lr+1];
        for(int ai = a_start; ai < a_end; ++ai){
            int j = A_local.col_idx[ai];
            double aij = A_local.vals[ai];
            if(j >= 0 && j < x_len) s += aij * x_dense[j];
        }
        y_local[lr] = s;
    }

    // Gather local row counts to root
    int local_rows = local_nrows;
    vector<int> all_counts(size);
    MPI_Gather(&local_rows, 1, MPI_INT, all_counts.data(), 1, MPI_INT, 0, MPI_COMM_WORLD);

    vector<int> displs(size,0);
    int total_rows = 0;
    if(rank == 0){
        for(int i=0;i<size;++i){ displs[i] = total_rows; total_rows += all_counts[i]; }
    }

    // Gather results to root
    vector<double> y_all(total_rows);
    MPI_Gatherv(y_local.data(), local_rows, MPI_DOUBLE, y_all.data(), all_counts.data(), displs.data(), MPI_DOUBLE, 0, MPI_COMM_WORLD);

    if(rank == 0){
        // write output as n x 1 coordinate file with nonzeros only
        vector<pair<int,double>> nz;
        nz.reserve(total_rows);
        for(int i=0;i<total_rows;++i){ if(fabs(y_all[i]) > tol) nz.push_back({i, y_all[i]}); }
        ofstream out(OutPath);
        if(!out){ cerr << "Failed to open output file: " << OutPath << endl; MPI_Abort(MPI_COMM_WORLD, 6); }
        out << "%%MatrixMarket matrix coordinate real general\n";
        out << "% Produced by spmv_mpi\n";
        out << A_nrows << " " << 1 << " " << nz.size() << "\n";
        out << setprecision(12);
        for(auto &t : nz){ out << (t.first + 1) << " " << 1 << " " << t.second << "\n"; }
        out.close();
        cerr << "Wrote output: " << OutPath << " (nnz=" << nz.size() << ")\n";
    }

    MPI_Finalize();
    return 0;
}