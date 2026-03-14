#include "scanner.h"
#include "thread_pool.h"

#include <filesystem>
#include <fstream>
#include <windows.h>
#include <unordered_set>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <sstream>

namespace fs = std::filesystem;

std::unordered_set<std::string> visited_files;
std::mutex visited_mutex;

std::queue<std::string> dir_queue;

std::mutex queue_mutex;
std::condition_variable queue_cv;

std::atomic<int> active_tasks(0);

uint64_t total_size = 0;
std::mutex size_mutex;


/* Enable backup privilege */

void enable_privilege()
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


/* NTFS hardlink ID */

std::string get_file_id(const std::string &path)
{
    HANDLE hFile = CreateFileA(
        path.c_str(),
        0,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if (hFile == INVALID_HANDLE_VALUE)
        return "";

    BY_HANDLE_FILE_INFORMATION info;

    if (!GetFileInformationByHandle(hFile, &info))
    {
        CloseHandle(hFile);
        return "";
    }

    CloseHandle(hFile);

    std::stringstream ss;

    ss << info.dwVolumeSerialNumber
       << "-"
       << info.nFileIndexHigh
       << "-"
       << info.nFileIndexLow;

    return ss.str();
}


/* Skip extremely slow system folders */

bool should_skip(const std::string &path)
{
    if (path.find("System Volume Information") != std::string::npos)
        return true;

    if (path.find("$Recycle.Bin") != std::string::npos)
        return true;

    if (path.find("Windows\\WinSxS") != std::string::npos)
        return true;

    if (path.find("Windows\\Installer") != std::string::npos)
        return true;

    if (path.find("DriverStore") != std::string::npos)
        return true;

    return false;
}


/* Worker thread */

void worker()
{
    while (true)
    {
        std::string dir;

        {
            std::unique_lock<std::mutex> lock(queue_mutex);

            queue_cv.wait(lock, [] {
                return !dir_queue.empty() || active_tasks == 0;
            });

            if (dir_queue.empty() && active_tasks == 0)
                return;

            dir = dir_queue.front();
            dir_queue.pop();

            active_tasks++;
        }

        if (!should_skip(dir))
        {
            try
            {
                for (auto &entry : fs::directory_iterator(dir, fs::directory_options::skip_permission_denied))
                {
                    try
                    {
                        if (entry.is_symlink())
                            continue;

                        if (entry.is_directory())
                        {
                            {
                                std::lock_guard<std::mutex> lock(queue_mutex);
                                dir_queue.push(entry.path().string());
                            }

                            queue_cv.notify_one();
                        }

                        else if (entry.is_regular_file())
                        {
                            std::string file = entry.path().string();

                            bool check_hardlinks =
                                file.find("WinSxS") != std::string::npos;

                            if (check_hardlinks)
                            {
                                std::string id = get_file_id(file);

                                if (!id.empty())
                                {
                                    std::lock_guard<std::mutex> lock(visited_mutex);

                                    if (!visited_files.insert(id).second)
                                        continue;
                                }
                            }

                            DWORD high;
                            DWORD low = GetCompressedFileSizeA(file.c_str(), &high);

                            uint64_t real_size =
                                ((uint64_t)high << 32) | low;

                            std::lock_guard<std::mutex> lock(size_mutex);
                            total_size += real_size;
                        }
                    }
                    catch (...)
                    {
                        continue;
                    }
                }
            }
            catch (...)
            {
            }
        }

        active_tasks--;

        queue_cv.notify_all();
    }
}


/* Main scan */

Node scan_directory_parallel(const std::string &root)
{
    Node node;

    node.name = root;
    node.size = 0;

    total_size = 0;
    visited_files.clear();

    while (!dir_queue.empty())
        dir_queue.pop();

    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        dir_queue.push(root);
    }

    active_tasks = 0;

    size_t threads = std::thread::hardware_concurrency();

    std::vector<std::thread> workers;

    for (size_t i = 0; i < threads; i++)
        workers.emplace_back(worker);

    queue_cv.notify_all();

    for (auto &t : workers)
        t.join();

    node.size = total_size;

    return node;
}


/* JSON output */

std::string escape_json(const std::string &str)
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


void write_json_node(std::ofstream &file, const Node &node, int indent = 0)
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

        file << "\n"
             << space << "  ]";
    }

    file << "\n"
         << space << "}";
}


void write_json(const Node &root)
{
    std::ofstream file("output/scan_result.json");

    write_json_node(file, root);

    file.close();
}