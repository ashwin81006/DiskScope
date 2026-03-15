#include "scanner.h"

#include <windows.h>
#include <iostream>
#include <queue>
#include <mutex>
#include <thread>
#include <vector>
#include <atomic>
#include <unordered_set>
#include <sstream>
#include <fstream>

std::queue<std::wstring> dir_queue;
std::mutex queue_mutex;

std::unordered_set<std::string> visited_files;
std::mutex file_mutex;

std::atomic<uint64_t> total_size(0);
std::atomic<uint64_t> files_scanned(0);
std::atomic<uint64_t> dirs_scanned(0);

std::atomic<int> active_workers(0);

bool finished = false;



/* Enable backup privilege */

void enable_backup_privilege()
{
    HANDLE token;
    TOKEN_PRIVILEGES tp;

    if(!OpenProcessToken(GetCurrentProcess(),
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

std::string get_file_id(const std::wstring& path)
{
    HANDLE file = CreateFileW(
        path.c_str(),
        0,
        FILE_SHARE_READ |
        FILE_SHARE_WRITE |
        FILE_SHARE_DELETE,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if(file == INVALID_HANDLE_VALUE)
        return "";

    BY_HANDLE_FILE_INFORMATION info;

    if(!GetFileInformationByHandle(file,&info))
    {
        CloseHandle(file);
        return "";
    }

    CloseHandle(file);

    std::stringstream ss;

    ss << info.dwVolumeSerialNumber
       << "-"
       << info.nFileIndexHigh
       << "-"
       << info.nFileIndexLow;

    return ss.str();
}



/* Actual disk allocation size */

uint64_t get_real_file_size(const std::wstring& path)
{
    DWORD high;

    DWORD low = GetCompressedFileSizeW(
        path.c_str(),
        &high);

    if(low == INVALID_FILE_SIZE &&
       GetLastError() != NO_ERROR)
        return 0;

    uint64_t size =
        ((uint64_t)high << 32) | low;

    return size;
}



/* Worker thread */

void worker()
{
    while(true)
    {
        std::wstring dir;

        {
            std::unique_lock<std::mutex> lock(queue_mutex);

            if(dir_queue.empty())
            {
                if(active_workers == 0)
                    return;

                lock.unlock();
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(1));
                continue;
            }

            dir = dir_queue.front();
            dir_queue.pop();

            active_workers++;
        }

        dirs_scanned++;

        if(dirs_scanned % 500 == 0)
        {
            std::wcout
            << L"\nScanning: "
            << dir
            << L"\nDirs: "
            << dirs_scanned
            << L" Files: "
            << files_scanned
            << L" Size: "
            << total_size/(1024ULL*1024ULL*1024ULL)
            << L" GB\n";
        }

        std::wstring search = dir + L"\\*";

        WIN32_FIND_DATAW data;

        HANDLE h = FindFirstFileW(
            search.c_str(),
            &data);

        if(h != INVALID_HANDLE_VALUE)
        {
            do
            {
                std::wstring name =
                    data.cFileName;

                if(name == L"." ||
                   name == L"..")
                    continue;

                std::wstring full =
                    dir + L"\\" + name;

                if(data.dwFileAttributes &
                   FILE_ATTRIBUTE_REPARSE_POINT)
                    continue;

                if(data.dwFileAttributes &
                   FILE_ATTRIBUTE_DIRECTORY)
                {
                    std::lock_guard<std::mutex>
                        lock(queue_mutex);

                    dir_queue.push(full);
                }

                else
                {
                    std::string id =
                        get_file_id(full);

                    if(!id.empty())
                    {
                        std::lock_guard<std::mutex>
                            lock(file_mutex);

                        if(!visited_files
                           .insert(id).second)
                            continue;
                    }

                    uint64_t size =
                        get_real_file_size(full);

                    total_size += size;

                    files_scanned++;
                }

            } while(FindNextFileW(h,&data));

            FindClose(h);
        }

        active_workers--;
    }
}



/* Main scan */

Node scan_directory_parallel(const std::string& root_path)
{
    Node root;

    root.name = root_path;

    total_size = 0;
    files_scanned = 0;
    dirs_scanned = 0;

    std::wstring root_w(
        root_path.begin(),
        root_path.end());

    {
        std::lock_guard<std::mutex>
            lock(queue_mutex);

        dir_queue.push(root_w);
    }

    int threads =
        std::thread::hardware_concurrency();

    std::vector<std::thread> workers;

    for(int i=0;i<threads;i++)
        workers.emplace_back(worker);

    for(auto& t:workers)
        t.join();

    root.size = total_size;

    std::cout
    << "\n\nSCAN COMPLETE\n";

    std::cout
    << "Files scanned: "
    << files_scanned
    << "\n";

    std::cout
    << "Directories: "
    << dirs_scanned
    << "\n";

    std::cout
    << "Total size: "
    << total_size
    << " bytes\n";

    return root;
}



/* JSON */

void write_json(const Node& root)
{
    std::ofstream file(
        "output/scan_result.json");

    file << "{\n";
    file << "  \"name\": \""
         << root.name
         << "\",\n";

    file << "  \"size\": "
         << root.size
         << "\n";

    file << "}\n";

    file.close();
}