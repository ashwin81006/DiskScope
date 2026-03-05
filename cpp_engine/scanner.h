#pragma once
#include <string>
#include <vector>
#include <cstdint>
#include "thread_pool.h"

struct Node {
    std::string name;
    uintmax_t size;
    std::vector<Node> children;
};

Node scan_directory(const std::string& path);
void write_json(const Node& root);