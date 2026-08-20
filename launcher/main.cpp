#include <windows.h>
#include <shellapi.h>
#include <string>
#include <vector>

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    // Get current executable directory
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t pos = dir.find_last_of(L"\\/");
    if (pos != std::wstring::npos) {
        dir = dir.substr(0, pos);
    }

    // Check for local pythonw.exe in app directory
    std::wstring pythonPath = dir + L"\\pythonw.exe";
    if (GetFileAttributesW(pythonPath.c_str()) == INVALID_FILE_ATTRIBUTES) {
        pythonPath = L"pythonw.exe";
    }

    // Launch the real notification-area controller.  The previous launcher
    // opened ai_ime_gui.py, a floating window with no tray icon, so users had
    // no reliable taskbar ON/OFF switch.
    std::wstring scriptPath = dir + L"\\ai_ime_tray.py";
    std::wstring cmdLine = L"\"" + pythonPath + L"\" \"" + scriptPath + L"\"";
    if (pCmdLine && wcslen(pCmdLine) > 0) {
        cmdLine += L" ";
        cmdLine += pCmdLine;
    }

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::vector<wchar_t> cmdBuf(cmdLine.begin(), cmdLine.end());
    cmdBuf.push_back(L'\0');

    if (CreateProcessW(NULL, cmdBuf.data(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, dir.c_str(), &si, &pi)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        return 0;
    }

    MessageBoxW(NULL, L"AI IME Tray could not be started.", L"Mozc AI IME", MB_ICONERROR);
    return 1;
}
