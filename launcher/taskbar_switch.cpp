// Mozc AI IME Taskbar Controller (Native Win32, 0 MB VRAM when OFF)
#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE

#include <windows.h>
#include <shellapi.h>
#include <tlhelp32.h>
#include <string>
#include <vector>

#define WM_TRAYICON (WM_USER + 1)
#define ID_TRAY_TOGGLE 1001
#define ID_TRAY_STATUS 1002
#define ID_TRAY_EXIT   1003
#define ID_BTN_TOGGLE  2001

HINSTANCE g_hInst = NULL;
HWND g_hWnd = NULL;
NOTIFYICONDATAW g_nid = { sizeof(NOTIFYICONDATAW) };
bool g_isAIOn = false;
bool g_isLoading = false;
HANDLE g_hServerProcess = NULL;
HWND g_hBtnToggle = NULL;
HWND g_hStatusLbl = NULL;

std::wstring GetAppDir() {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(NULL, path, MAX_PATH);
    std::wstring p(path);
    size_t pos = p.find_last_of(L"\\/");
    return (pos != std::wstring::npos) ? p.substr(0, pos) : L".";
}

void KillAIProcess() {
    if (g_hServerProcess) {
        TerminateProcess(g_hServerProcess, 0);
        CloseHandle(g_hServerProcess);
        g_hServerProcess = NULL;
    }
    // Also cleanup any orphan ranker python processes
    system("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq *ranker*\" >nul 2>&1");
    system("taskkill /F /IM pythonw.exe /FI \"WINDOWTITLE eq *ranker*\" >nul 2>&1");
}

HICON CreateAIIcon(bool on, bool loading) {
    int w = 32, h = 32;
    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);
    HBITMAP hbmColor = CreateCompatibleBitmap(hdcScreen, w, h);
    HBITMAP hbmMask = CreateBitmap(w, h, 1, 1, NULL);

    HBITMAP hOld = (HBITMAP)SelectObject(hdcMem, hbmColor);

    // Draw background circle
    COLORREF bgColor = on ? RGB(40, 190, 60) : (loading ? RGB(230, 160, 20) : RGB(80, 85, 100));
    HBRUSH hBrush = CreateSolidBrush(bgColor);
    HPEN hPen = CreatePen(PS_SOLID, 1, bgColor);
    SelectObject(hdcMem, hBrush);
    SelectObject(hdcMem, hPen);
    Ellipse(hdcMem, 1, 1, w - 2, h - 2);

    // Draw Text "AI"
    SetBkMode(hdcMem, TRANSPARENT);
    SetTextColor(hdcMem, on ? RGB(10, 30, 10) : RGB(255, 255, 255));
    HFONT hFont = CreateFontW(14, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                             DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                             CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
    HFONT hOldFont = (HFONT)SelectObject(hdcMem, hFont);
    RECT rc = { 0, 0, w, h };
    DrawTextW(hdcMem, L"AI", -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);

    SelectObject(hdcMem, hOldFont);
    SelectObject(hdcMem, hOld);
    DeleteObject(hFont);
    DeleteObject(hBrush);
    DeleteObject(hPen);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);

    ICONINFO ii = { 0 };
    ii.fIcon = TRUE;
    ii.hbmColor = hbmColor;
    ii.hbmMask = hbmMask;
    HICON hIcon = CreateIconIndirect(&ii);

    DeleteObject(hbmColor);
    DeleteObject(hbmMask);
    return hIcon;
}

void UpdateUI() {
    HICON hIcon = CreateAIIcon(g_isAIOn, g_isLoading);
    SendMessage(g_hWnd, WM_SETICON, ICON_BIG, (LPARAM)hIcon);
    SendMessage(g_hWnd, WM_SETICON, ICON_SMALL, (LPARAM)hIcon);

    g_nid.hIcon = hIcon;
    if (g_isAIOn) {
        wcscpy_s(g_nid.szTip, L"Mozc AI IME: 稼働中 (ON / 21.9ms / VRAM: 1.2GB)");
        SetWindowTextW(g_hStatusLbl, L"● AI変換: 稼働中 (ON)\nGPU (VRAM 1.2GB) で文脈推論中");
        SetWindowTextW(g_hBtnToggle, L"⏹ AI IME を停止する (OFF / VRAM解放)");
        EnableWindow(g_hBtnToggle, TRUE);
    } else if (g_isLoading) {
        wcscpy_s(g_nid.szTip, L"Mozc AI IME: GPUにロード中 (約3秒)...");
        SetWindowTextW(g_hStatusLbl, L"⏳ ロード中 (約3秒)...\nRuri-310M を CUDA に展開しています");
        SetWindowTextW(g_hBtnToggle, L"ロード中...");
        EnableWindow(g_hBtnToggle, FALSE);
    } else {
        wcscpy_s(g_nid.szTip, L"Mozc AI IME: 待機中 (OFF / VRAM: 0 MB)");
        SetWindowTextW(g_hStatusLbl, L"● AI変換: 停止中 (OFF)\n通常の爆速Mozcとして動作中 (VRAM: 0 MB)");
        SetWindowTextW(g_hBtnToggle, L"⚡ AI IME を開始する (ON)");
        EnableWindow(g_hBtnToggle, TRUE);
    }
    Shell_NotifyIconW(NIM_MODIFY, &g_nid);
}

DWORD WINAPI StartServerThread(LPVOID lpParam) {
    g_isLoading = true;
    UpdateUI();

    std::wstring appDir = GetAppDir();
    std::wstring pythonPath = L"pythonw.exe";
    std::wstring scriptPath = appDir + L"\\ranker\\ranker.py";

    std::wstring cmdLine = L"\"" + pythonPath + L"\" \"" + scriptPath + L"\" --pipe ai_ime_ranker --backend ruri --no-ui";

    STARTUPINFOW si = { sizeof(STARTUPINFOW) };
    PROCESS_INFORMATION pi = { 0 };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::vector<wchar_t> cmdBuf(cmdLine.begin(), cmdLine.end());
    cmdBuf.push_back(L'\0');

    BOOL success = CreateProcessW(
        NULL, cmdBuf.data(), NULL, NULL, FALSE,
        CREATE_NO_WINDOW, NULL, appDir.c_str(), &si, &pi
    );

    if (success) {
        g_hServerProcess = pi.hProcess;
        CloseHandle(pi.hThread);
        Sleep(7000); // Wait for Ruri-310M load
        g_isAIOn = true;
    } else {
        MessageBoxW(g_hWnd, L"AIエンジンの起動に失敗しました。", L"エラー", MB_OK | MB_ICONERROR);
        g_isAIOn = false;
    }
    g_isLoading = false;
    UpdateUI();
    return 0;
}

void ToggleAI() {
    if (g_isLoading) return;

    if (g_isAIOn) {
        KillAIProcess();
        g_isAIOn = false;
        UpdateUI();
    } else {
        CreateThread(NULL, 0, StartServerThread, NULL, 0, NULL);
    }
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_CREATE: {
        // Status label
        g_hStatusLbl = CreateWindowW(
            L"STATIC", L"● AI変換: 停止中 (OFF)\n通常の爆速Mozcとして動作中 (VRAM: 0 MB)",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            20, 20, 320, 48, hWnd, NULL, g_hInst, NULL
        );

        // Toggle Button
        g_hBtnToggle = CreateWindowW(
            L"BUTTON", L"⚡ AI IME を開始する (ON)",
            WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON | BS_DEFPUSHBUTTON,
            30, 80, 300, 40, hWnd, (HMENU)ID_BTN_TOGGLE, g_hInst, NULL
        );
        break;
    }
    case WM_COMMAND:
        if (LOWORD(wParam) == ID_BTN_TOGGLE) {
            ToggleAI();
        }
        break;
    case WM_TRAYICON:
        if (lParam == WM_RBUTTONUP) {
            POINT pt;
            GetCursorPos(&pt);
            HMENU hMenu = CreatePopupMenu();
            AppendMenuW(hMenu, MF_STRING, ID_TRAY_TOGGLE, g_isAIOn ? L"⏹ AI IME を無効化 (OFF)" : L"⚡ AI IME を有効化 (ON)");
            AppendMenuW(hMenu, MF_SEPARATOR, 0, NULL);
            AppendMenuW(hMenu, MF_STRING, ID_TRAY_EXIT, L"コントローラーを終了");

            SetForegroundWindow(hWnd);
            int cmd = TrackPopupMenu(hMenu, TPM_RETURNCMD | TPM_NONOTIFY, pt.x, pt.y, 0, hWnd, NULL);
            DestroyMenu(hMenu);

            if (cmd == ID_TRAY_TOGGLE) {
                ToggleAI();
            } else if (cmd == ID_TRAY_EXIT) {
                DestroyWindow(hWnd);
            }
        } else if (lParam == WM_LBUTTONUP) {
            ShowWindow(hWnd, SW_SHOWNORMAL);
            SetForegroundWindow(hWnd);
        }
        break;
    case WM_SYSCOMMAND:
        if ((wParam & 0xFFF0) == SC_MINIMIZE) {
            ShowWindow(hWnd, SW_HIDE);
            return 0;
        }
        break;
    case WM_CLOSE:
        ShowWindow(hWnd, SW_HIDE);
        return 0; // Hide instead of closing when X is pressed
    case WM_DESTROY:
        KillAIProcess();
        Shell_NotifyIconW(NIM_DELETE, &g_nid);
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProcW(hWnd, msg, wParam, lParam);
    }
    return 0;
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE, PWSTR, int) {
    g_hInst = hInstance;

    // Single instance check
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"Mozc_AI_Taskbar_Controller_Mutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        HWND hExisting = FindWindowW(L"MozcAITaskbarClass", NULL);
        if (hExisting) {
            ShowWindow(hExisting, SW_SHOWNORMAL);
            SetForegroundWindow(hExisting);
        }
        return 0;
    }

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"MozcAITaskbarClass";
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClassExW(&wc);

    int w = 380, h = 180;
    int x = (GetSystemMetrics(SM_CXSCREEN) - w) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - h) / 2;

    g_hWnd = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_APPWINDOW,
        L"MozcAITaskbarClass", L"Mozc AI IME コントローラー",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        x, y, w, h, NULL, NULL, hInstance, NULL
    );

    // Setup Tray Icon
    g_nid.hWnd = g_hWnd;
    g_nid.uID = 1;
    g_nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    g_nid.uCallbackMessage = WM_TRAYICON;
    HICON hIcon = CreateAIIcon(false, false);
    g_nid.hIcon = hIcon;
    wcscpy_s(g_nid.szTip, L"Mozc AI IME: 待機中 (OFF / VRAM: 0 MB)");
    Shell_NotifyIconW(NIM_ADD, &g_nid);

    UpdateUI();
    ShowWindow(g_hWnd, SW_SHOWNORMAL);
    UpdateWindow(g_hWnd);
    SetForegroundWindow(g_hWnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    ReleaseMutex(hMutex);
    CloseHandle(hMutex);
    return (int)msg.wParam;
}
