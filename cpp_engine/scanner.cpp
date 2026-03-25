#include "scanner.h"

#include <windows.h>
#include <iostream>
#include <queue>
#include <mutex>
#include <algorithm>
#include <thread>
#include <chrono>
#include <iomanip>
#include <vector>
#include <atomic>
#include <unordered_set>
#include <sstream>
#include <fstream>
#include <cstdio>

struct WorkItem
{
    std::wstring path;
    Node *node;
};

struct LargeFile
{
    std::string path;
    uint64_t size;
};

std::vector<LargeFile> largest_files;
std::mutex largest_mutex;

std::queue<WorkItem> dir_queue;
std::mutex queue_mutex;

std::unordered_set<uint64_t> visited_files;
std::mutex file_mutex;

uint64_t cluster_size = 4096;

std::atomic<uint64_t> total_size(0);
std::atomic<uint64_t> files_scanned(0);
std::atomic<uint64_t> dirs_scanned(0);
std::atomic<int> active_workers(0);

/* ---------- UTIL ---------- */

void detect_cluster_size(const std::wstring &root)
{
    DWORD sectors, bytes, free_clusters, total_clusters;

    if (GetDiskFreeSpaceW(root.c_str(), &sectors, &bytes, &free_clusters, &total_clusters))
    {
        cluster_size = (uint64_t)sectors * bytes;
    }
}

uint64_t align_cluster(uint64_t size)
{
    if (size == 0)
        return 0;
    uint64_t rem = size % cluster_size;
    return rem == 0 ? size : size + (cluster_size - rem);
}

void enable_backup_privilege()
{
    HANDLE token;
    TOKEN_PRIVILEGES tp;

    if (!OpenProcessToken(GetCurrentProcess(),
                          TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                          &token))
        return;

    LookupPrivilegeValue(NULL, SE_BACKUP_NAME, &tp.Privileges[0].Luid);

    tp.PrivilegeCount = 1;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    AdjustTokenPrivileges(token, FALSE, &tp, sizeof(tp), NULL, NULL);
    CloseHandle(token);
}

uint64_t get_file_id(const std::wstring &path)
{
    HANDLE file = CreateFileW(
        path.c_str(), 0,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL, OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL, NULL);

    if (file == INVALID_HANDLE_VALUE)
        return 0;

    BY_HANDLE_FILE_INFORMATION info;

    if (!GetFileInformationByHandle(file, &info))
    {
        CloseHandle(file);
        return 0;
    }

    CloseHandle(file);

    return ((uint64_t)info.dwVolumeSerialNumber << 32) |
           ((uint64_t)info.nFileIndexHigh << 16) |
           info.nFileIndexLow;
}

uint64_t get_real_file_size(const std::wstring &path)
{
    DWORD high;
    DWORD low = GetCompressedFileSizeW(path.c_str(), &high);

    if (low == INVALID_FILE_SIZE && GetLastError() != NO_ERROR)
        return 0;

    return ((uint64_t)high << 32) | low;
}

/* ---------- WORKER ---------- */

void worker()
{
    while (true)
    {
        WorkItem item;

        {
            std::unique_lock<std::mutex> lock(queue_mutex);

            if (dir_queue.empty())
            {
                if (active_workers == 0)
                    break; // 🔥 BREAK instead of return

                lock.unlock();
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }

            item = dir_queue.front();
            dir_queue.pop();
            active_workers++;
        }

        std::wstring dir = item.path;
        Node *node = item.node;

        dirs_scanned++;

        std::wstring search = dir + L"\\*";
        WIN32_FIND_DATAW data;

        HANDLE h = FindFirstFileW(search.c_str(), &data);

        if (h != INVALID_HANDLE_VALUE)
        {
            do
            {
                std::wstring name = data.cFileName;

                if (name == L"." || name == L"..")
                    continue;

                std::wstring full = dir + L"\\" + name;

                if (data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
                    continue;

                if (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
                {
                    Node *child = new Node;
                    child->name = std::string(name.begin(), name.end());
                    child->path = std::string(full.begin(), full.end());

                    node->dir_count++;

                    {
                        std::lock_guard<std::mutex> lock(queue_mutex);
                        node->children.push_back(child);
                        dir_queue.push({full, child});
                    }
                }
                else
                {
                    uint64_t id = get_file_id(full);

                    if (id != 0)
                    {
                        std::lock_guard<std::mutex> lock(file_mutex);
                        if (!visited_files.insert(id).second)
                            continue;
                    }

                    uint64_t size = get_real_file_size(full);

                    // fallback if API fails
                    if (size == 0)
                    {
                        size = ((uint64_t)data.nFileSizeHigh << 32) |
                               data.nFileSizeLow;
                    }

                    // node->size += size;
                    node->file_count++;
                    total_size += size;
                    files_scanned++;

                    // 🔥 ADD THIS BLOCK (DO NOT REMOVE ANYTHING ABOVE)
                    Node *file_node = new Node;
                    file_node->name = std::string(name.begin(), name.end());
                    file_node->path = std::string(full.begin(), full.end());
                    file_node->size = size;
                    file_node->file_count = 0;
                    file_node->dir_count = 0;

                    {
                        std::lock_guard<std::mutex> lock(queue_mutex);
                        node->children.push_back(file_node);
                    }
                    // 🔥 END ADD

                    if (files_scanned % 1000 == 0)
                    {
                        int percent = (int)((files_scanned * 100) / (files_scanned + dir_queue.size() + 1));

                        if (percent > 99)
                            percent = 99;

                        std::cout << "PROGRESS:" << percent << std::endl;
                    }

                    /* track large files */
                    {
                        std::lock_guard<std::mutex> lock(largest_mutex);

                        largest_files.push_back({std::string(full.begin(), full.end()),
                                                 size});

                        if (largest_files.size() > 200)
                        {
                            std::sort(largest_files.begin(), largest_files.end(),
                                      [](auto &a, auto &b)
                                      { return a.size > b.size; });

                            largest_files.resize(100);
                        }
                    }
                }
            } while (FindNextFileW(h, &data));

            FindClose(h);
        }

        active_workers--;
    }
}

/* ---------- TREE ---------- */

void sort_tree(Node *node)
{
    std::sort(node->children.begin(), node->children.end(),
              [](Node *a, Node *b)
              { return a->size > b->size; });

    for (auto *c : node->children)
        sort_tree(c);
}

uint64_t compute_sizes(Node *node)
{
    uint64_t total = node->size;

    for (auto *child : node->children)
    {
        total += compute_sizes(child);
        node->file_count += child->file_count;
        node->dir_count += child->dir_count;
    }

    node->size = total;
    return total;
}

/* ---------- SCAN ---------- */

Node scan_directory_parallel(const std::string &root_path)
{
    enable_backup_privilege();

    Node root;
    root.name = root_path;
    root.path = root_path;

    total_size = 0;
    files_scanned = 0;
    dirs_scanned = 0;

    std::wstring root_w(root_path.begin(), root_path.end());
    detect_cluster_size(root_w);

    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        dir_queue.push({root_w, &root});
    }

    int threads = std::thread::hardware_concurrency();
    std::vector<std::thread> workers;

    for (int i = 0; i < threads; i++)
        workers.emplace_back(worker);

    for (auto &t : workers)
        t.join();
    dir_queue = std::queue<WorkItem>();
    std::cout << "DONE" << std::endl;

    compute_sizes(&root);
    sort_tree(&root);

    return root;
}

/* ---------- JSON ---------- */
std::string escape_json(const std::string &s)
{
    std::ostringstream o;
    for (unsigned char c : s)
    {
        switch (c)
        {
        case '"':
            o << "\\\"";
            break;
        case '\\':
            o << "\\\\";
            break;
        case '\n':
            o << "\\n";
            break;
        case '\r':
            o << "\\r";
            break;
        case '\t':
            o << "\\t";
            break;
        case '\f':
            o << "\\f";
            break; // form feed
        case '\b':
            o << "\\b";
            break; // backspace
        default:
            if (c < 0x20) // any other control character
            {
                o << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << (int)c;
            }
            else
            {
                o << c;
            }
        }
    }
    return o.str();
}

void write_node(std::ofstream &f, Node *node, int depth)
{
    std::string indent(depth * 2, ' ');

    f << indent << "{\n";
    f << indent << "  \"name\": \"" << escape_json(node->name) << "\",\n";
    f << indent << "  \"path\": \"" << escape_json(node->path) << "\",\n";
    f << indent << "  \"size\": " << node->size << ",\n";
    f << indent << "  \"files\": " << node->file_count << ",\n";
    f << indent << "  \"dirs\": " << node->dir_count;

    if (!node->children.empty())
    {
        f << ",\n";
        f << indent << "  \"children\": [\n";

        for (size_t i = 0; i < node->children.size(); i++)
        {
            write_node(f, node->children[i], depth + 2);

            if (i + 1 < node->children.size())
                f << ",\n";
        }

        f << "\n"
          << indent << "  ]";
    }

    f << "\n"
      << indent << "}";
}

void write_json(const Node &root)
{
    std::ofstream file("output/scan_result.tmp");

    file << "{\n";

    file << "  \"scan_info\": {\n";
    file << "    \"files\": " << files_scanned << ",\n";
    file << "    \"dirs\": " << dirs_scanned << ",\n";
    file << "    \"size\": " << total_size << "\n";
    file << "  },\n";

    file << "  \"tree\": ";
    write_node(file, const_cast<Node *>(&root), 1);
    file << ",\n";

    file << "  \"largest_files\": [\n";

    for (size_t i = 0; i < largest_files.size(); i++)
    {
        file << "    {\"path\": \""
             << escape_json(largest_files[i].path)
             << "\", \"size\": "
             << largest_files[i].size << "}";

        if (i + 1 < largest_files.size())
            file << ",";

        file << "\n";
    }

    file << "  ]\n";
    file << "}\n";

    file.close();

    std::remove("output/scan_result.json");
    std::rename("output/scan_result.tmp", "output/scan_result.json");
}