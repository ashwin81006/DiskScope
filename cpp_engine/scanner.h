#pragma once

#include <string>
#include <cstdint>
#include <vector>
struct Node
{
    std::string name;
    std::string path;
    uint64_t size = 0;
    uint64_t file_count = 0;
    uint64_t dir_count = 0;
    std::vector<Node *> children;
};

Node scan_directory_parallel(const std::string &path);
void write_json(const Node &root);