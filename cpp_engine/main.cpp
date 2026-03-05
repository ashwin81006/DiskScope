#include <iostream>
#include "scanner.h"
using namespace std;
int main(int argc, char* argv[]) {

    if (argc < 2) {
        cout << "Usage: scanner <path>\n";
        return 1;
    }

    string path = argv[1];

    cout << "Scanning: " << path << endl;

    auto root = scan_directory(path);

    cout << "Total size: " << root.size << " bytes\n";

    write_json(root);

    cout << "Scan complete. Output written to output/scan_result.json\n";

    return 0;
}