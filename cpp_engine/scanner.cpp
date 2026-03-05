#include "scanner.h"
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;
std::string escape_json(const std::string& str) {
    std::string result;

    for (char c : str) {
        if (c == '\\')
            result += "\\\\";
        else
            result += c;
    }

    return result;
}

Node scan_directory(const std::string& path) {

    Node node;
    node.name = path;
    node.size = 0;

    for (auto& entry : fs::directory_iterator(path)) {

        try {

            if (entry.is_directory()) {

                Node child = scan_directory(entry.path().string());
                node.size += child.size;
                node.children.push_back(child);

            } else {

                auto size = entry.file_size();
                node.size += size;

            }

        } catch (...) {
            continue;
        }
    }

    return node;
}

void write_json(const Node& root) {

    std::ofstream file("output/scan_result.json");

    file << "{\n";
    file << "\"name\": \"" << escape_json(root.name) << "\",\n";
    file << "\"size\": " << root.size << "\n";
    file << "}\n";

    file.close();
}