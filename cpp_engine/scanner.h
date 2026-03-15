#pragma once

#include <string>
#include <cstdint>

struct Node
{
    std::string name;
    uint64_t size;
};

Node scan_directory_parallel(const std::string& path);
void write_json(const Node& root);