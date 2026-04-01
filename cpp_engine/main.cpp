#include <iostream>
#include "scanner.h"
#include <conio.h>

using namespace std;
int main(int argc,char* argv[])
{
    if(argc < 2)
    {
        cout<<"Usage: scanner <path>\n";
        return 1;
    }

    string path = argv[1];

    cout<<"Scanning: "<<path<<"\n";

    Node root = scan_directory_parallel(path);

    cout<<"Total size: "<<root.size<<" bytes\n";

    write_json(root);

    cout<<"JSON written\n";
    return 0;
}