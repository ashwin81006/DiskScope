#pragma once

#include <string>
#include <cstdint>
#include <vector>

struct Node
{
    std::string name;
    uint64_t size = 0;
    std::vector<Node*> children;
};

Node scan_directory_parallel(const std::string& path);
void write_json(const Node& root);