#include <iostream>
#include <conio.h>
#include "scanner.h"

using namespace std;

extern void enable_privilege();

int main(int argc, char* argv[])
{
    if(argc < 2)
    {
        cout << "Usage: scanner <path>\n";
        return 1;
    }

    enable_privilege();

    string path = argv[1];

    cout << "Scanning: " << path << endl;

    Node root = scan_directory_parallel(path);

    cout << "Total size: " << root.size << " bytes\n";

    write_json(root);

    cout << "Scan complete. Output written to output/scan_result.json\n";
    getch();
    return 0;
}