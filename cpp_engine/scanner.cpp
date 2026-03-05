#include "scanner.h"
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

Node scan_directory(const std::string& path)
{
    Node node;
    node.name = fs::path(path).filename().string();
    node.size = 0;

    for (auto& entry : fs::directory_iterator(path))
    {
        try
        {
            if (entry.is_directory())
            {
                Node child = scan_directory(entry.path().string());
                node.size += child.size;
                node.children.push_back(child);
            }
            else
            {
                node.size += entry.file_size();
            }
        }
        catch (...)
        {
            continue;
        }
    }

    return node;
}

std::string escape_json(const std::string& str)
{
    std::string result;

    for (char c : str)
    {
        if (c == '\\')
            result += "\\\\";
        else
            result += c;
    }

    return result;
}

void write_json_node(std::ofstream& file, const Node& node, int indent = 0)
{
    std::string space(indent, ' ');

    file << space << "{\n";

    file << space << "  \"name\": \"" << escape_json(node.name) << "\",\n";
    file << space << "  \"size\": " << node.size;

    if (!node.children.empty())
    {
        file << ",\n";
        file << space << "  \"children\": [\n";

        for (size_t i = 0; i < node.children.size(); ++i)
        {
            write_json_node(file, node.children[i], indent + 4);

            if (i < node.children.size() - 1)
                file << ",\n";
        }

        file << "\n" << space << "  ]";
    }

    file << "\n" << space << "}";
}
void write_json(const Node& root)
{
    std::ofstream file("output/scan_result.json");

    write_json_node(file, root);

    file.close();
}