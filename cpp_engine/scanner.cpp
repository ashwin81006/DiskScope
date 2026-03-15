#include "scanner.h"

#include <windows.h>
#include <iostream>
#include <queue>
#include <mutex>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>
#include <unordered_set>
#include <sstream>
#include <fstream>

std::queue<std::wstring> dir_queue;
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
        std::wstring dir;

        {
            std::unique_lock<std::mutex> lock(queue_mutex);

            if (dir_queue.empty())
            {
                if (active_workers == 0)
                {
                    return;
                }

                lock.unlock();
                std::this_thread::yield();
                continue;
            }
            dir = dir_queue.front();
            dir_queue.pop();

            active_workers++;
        }

        dirs_scanned++;

        if (dirs_scanned % 500 == 0)
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

        HANDLE h = FindFirstFileW(
            search.c_str(),
            &data);

        if (h != INVALID_HANDLE_VALUE)
        {
            do
            {
                std::wstring name =
                    data.cFileName;

                if (name == L"." ||
                    name == L"..")
                    continue;

                std::wstring full =
                    dir + L"\\" + name;

                if (data.dwFileAttributes &
                    FILE_ATTRIBUTE_REPARSE_POINT)
                    continue;

                if (data.dwFileAttributes &
                    FILE_ATTRIBUTE_DIRECTORY)
                {
                    std::lock_guard<std::mutex>
                        lock(queue_mutex);

                    dir_queue.push(full);
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

                    /* if compressed or sparse → use NTFS allocated size */
                    if (data.dwFileAttributes & FILE_ATTRIBUTE_COMPRESSED ||
                        data.dwFileAttributes & FILE_ATTRIBUTE_SPARSE_FILE)
                    {
                        size = get_real_file_size(full);
                    }
                    else
                    {
                        size = align_cluster(logical_size);
                    }


                    total_size += size;

                    files_scanned++;
                }

            } while (FindNextFileW(h, &data));

            FindClose(h);
        }

        active_workers--;
    }
}

/* Main scan */

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

        dir_queue.push(root_w);
    }

    int threads =
        std::thread::hardware_concurrency();

    std::vector<std::thread> workers;

    for (int i = 0; i < threads; i++)
        workers.emplace_back(worker);

    for (auto &t : workers)
        t.join();

    root.size = total_size;

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

void write_json(const Node &root)
{
    std::ofstream file("output/scan_result.json");

    file << "{\n";
    file << "  \"name\": \"" << root.name << "\",\n";
    file << "  \"size\": " << root.size << "\n";
    file << "}\n";

    file.close();
}