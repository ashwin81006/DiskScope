#include "scanner.h"

#include <windows.h>
#include <iostream>
#include <queue>
#include <mutex>
#include <algorithm>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>
#include <unordered_set>
#include <sstream>
#include <fstream>

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

bool finished = false;

/* Enable backup privilege */

void detect_cluster_size(const std::wstring &root)
{
    DWORD sectors, bytes, free_clusters, total_clusters;

    if (GetDiskFreeSpaceW(
            root.c_str(),
            &sectors,
            &bytes,
            &free_clusters,
            &total_clusters))
    {
        cluster_size = (uint64_t)sectors * bytes;
    }
}

uint64_t align_cluster(uint64_t size)
{
    if (size == 0)
        return 0;

    uint64_t remainder = size % cluster_size;

    if (remainder == 0)
        return size;

    return size + (cluster_size - remainder);
}
void enable_backup_privilege()
{
    HANDLE token;
    TOKEN_PRIVILEGES tp;

    if (!OpenProcessToken(GetCurrentProcess(),
                          TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                          &token))
        return;

    LookupPrivilegeValue(NULL,
                         SE_BACKUP_NAME,
                         &tp.Privileges[0].Luid);

    tp.PrivilegeCount = 1;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    AdjustTokenPrivileges(token,
                          FALSE,
                          &tp,
                          sizeof(tp),
                          NULL,
                          NULL);

    CloseHandle(token);
}

/* NTFS file unique id */

uint64_t get_file_id(const std::wstring &path)
{
    HANDLE file = CreateFileW(
        path.c_str(),
        0,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if (file == INVALID_HANDLE_VALUE)
        return 0;

    BY_HANDLE_FILE_INFORMATION info;

    if (!GetFileInformationByHandle(file, &info))
    {
        CloseHandle(file);
        return 0;
    }

    CloseHandle(file);

    uint64_t id =
        ((uint64_t)info.dwVolumeSerialNumber << 32) |
        ((uint64_t)info.nFileIndexHigh << 16) |
        info.nFileIndexLow;

    return id;
}
/* Actual disk allocation size */

uint64_t get_real_file_size(const std::wstring &path)
{
    DWORD high;

    DWORD low = GetCompressedFileSizeW(
        path.c_str(),
        &high);

    if (low == INVALID_FILE_SIZE &&
        GetLastError() != NO_ERROR)
        return 0;

    uint64_t size =
        ((uint64_t)high << 32) | low;

    return size;
}

/* Worker thread */

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
                    return;

                lock.unlock();
                std::this_thread::yield();
                continue;
            }

            item = dir_queue.front();
            dir_queue.pop();

            active_workers++;
        }

        std::wstring dir = item.path;
        Node *current_node = item.node;

        dirs_scanned++;

        if (dirs_scanned % 1000 == 0)
        {
            std::wcout
                << L"\nScanning: "
                << dir
                << L"\nDirs: "
                << dirs_scanned
                << L" Files: "
                << files_scanned
                << L" Size: "
                << total_size / (1024ULL * 1024ULL * 1024ULL)
                << L" GB\n";
        }

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

                    current_node->dir_count++; // ADD THIS

                    {
                        std::lock_guard<std::mutex> lock(queue_mutex);
                        current_node->children.push_back(child);
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

                    uint64_t logical_size =
                        ((uint64_t)data.nFileSizeHigh << 32) |
                        data.nFileSizeLow;

                    uint64_t size;

                    if (data.dwFileAttributes & FILE_ATTRIBUTE_COMPRESSED ||
                        data.dwFileAttributes & FILE_ATTRIBUTE_SPARSE_FILE)
                    {
                        size = get_real_file_size(full);
                    }
                    else
                    {
                        size = align_cluster(logical_size);
                    }

                    current_node->size += size;
                    current_node->file_count++;
                    total_size += size;
                    files_scanned++;

                    /* track largest files */
                    {
                        std::lock_guard<std::mutex> lock(largest_mutex);

                        LargeFile lf;
                        lf.path = std::string(full.begin(), full.end());
                        lf.size = size;

                        largest_files.push_back(lf);

                        if (largest_files.size() > 200)
                        {
                            std::sort(largest_files.begin(), largest_files.end(),
                                      [](const LargeFile &a, const LargeFile &b)
                                      {
                                          return a.size > b.size;
                                      });

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

/* Main scan */
void sort_tree(Node *node)
{
    std::sort(node->children.begin(), node->children.end(),
              [](Node *a, Node *b)
              {
                  return a->size > b->size;
              });

    for (Node *child : node->children)
        sort_tree(child);
}

uint64_t compute_directory_sizes(Node *node)
{
    uint64_t total = node->size;

    for (Node *child : node->children)
    {
        total += compute_directory_sizes(child);
        node->file_count += child->file_count;
        node->dir_count += child->dir_count;
    }

    node->size = total;
    return total;
}

Node scan_directory_parallel(const std::string &root_path)
{
    enable_backup_privilege();
    Node root;

    root.name = root_path;

    total_size = 0;
    files_scanned = 0;
    dirs_scanned = 0;

    std::wstring root_w(
        root_path.begin(),
        root_path.end());

    detect_cluster_size(root_w);
    {
        std::lock_guard<std::mutex>
            lock(queue_mutex);

        dir_queue.push({root_w, &root});
    }

    int threads =
        std::thread::hardware_concurrency();

    std::vector<std::thread> workers;

    for (int i = 0; i < threads; i++)
        workers.emplace_back(worker);

    for (auto &t : workers)
        t.join();
    compute_directory_sizes(&root);
    sort_tree(&root);
    std::cout << "\n\nSCAN COMPLETE\n";

    std::cout << "Files scanned: " << files_scanned << "\n";
    std::cout << "Directories: " << dirs_scanned << "\n";
    std::cout << "Total size: " << total_size << " bytes\n";

    double seconds = 1.0;
    seconds = (double)files_scanned / 25000.0;

    std::cout << "Approx scan speed: "
              << files_scanned / seconds
              << " files/sec\n";

    return root;
}

/* JSON */

std::string escape_json(const std::string &s)
{
    std::string out;

    for (char c : s)
    {
        if (c == '\\')
            out += "\\\\";
        else if (c == '"')
            out += "\\\"";
        else
            out += c;
    }

    return out;
}

void write_node(std::ofstream &f, Node *node, int depth)
{
    std::string indent(depth * 2, ' ');

    f << indent << "{\n";
    f << indent << "  \"name\": \"" << escape_json(node->name) << "\",\n";
    f << indent << "  \"size\": " << node->size;

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
    std::ofstream file("output/scan_result.json");

    file << "{\n";

    /* scan metadata */
    file << "  \"scan_info\": {\n";
    file << "    \"files\": " << files_scanned << ",\n";
    file << "    \"dirs\": " << dirs_scanned << ",\n";
    file << "    \"size\": " << total_size << "\n";
    file << "  },\n";

    /* tree */
    file << "  \"tree\": ";
    write_node(file, const_cast<Node*>(&root), 1);
    file << ",\n";

    /* largest files */
    file << "  \"largest_files\": [\n";

    for (size_t i = 0; i < largest_files.size(); i++)
    {
        file << "    {\"path\": \""
             << escape_json(largest_files[i].path)
             << "\", \"size\": "
             << largest_files[i].size
             << "}";

        if (i + 1 < largest_files.size())
            file << ",";

        file << "\n";
    }

    file << "  ]\n";

    file << "}\n";

    file.close();
}