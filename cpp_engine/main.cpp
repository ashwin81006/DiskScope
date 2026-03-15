#include <iostream>
#include "scanner.h"
#include <conio.h>
int main(int argc,char* argv[])
{
    if(argc < 2)
    {
        std::cout<<"Usage: scanner <path>\n";
        return 1;
    }

    std::string path = argv[1];

    std::cout<<"Scanning: "<<path<<"\n";

    Node root = scan_directory_parallel(path);

    std::cout<<"Total size: "<<root.size<<" bytes\n";

    write_json(root);

    std::cout<<"JSON written\n";
    getch();
    return 0;
}