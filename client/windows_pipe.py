"""Minimal Windows Named Pipe smoke-test client.

The Mozc production path uses the C++ client in ``mozc/``.  This Python helper
is intentionally small and is useful for verifying the resident process on a
developer workstation without installing pywin32.
"""

from __future__ import annotations

import ctypes
import json
import time
from typing import Any, Dict

from ranker.protocol import loads_strict, validate_request, validate_response


def rank_once(pipe_name: str, request: Dict[str, Any], timeout_ms: int = 200) -> Dict[str, Any]:
    if __import__("sys").platform != "win32":
        raise OSError("Windows Named Pipes are unavailable on this platform")
    request = validate_request(request)
    k32 = ctypes.windll.kernel32
    k32.WaitNamedPipeW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    k32.WaitNamedPipeW.restype = ctypes.c_int
    if not k32.WaitNamedPipeW(pipe_name, max(1, int(timeout_ms))):
        raise TimeoutError("ranker pipe is not ready")
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p]
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    k32.WriteFile.restype = ctypes.c_int
    k32.PeekNamedPipe.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32),
                                  ctypes.c_void_p]
    k32.PeekNamedPipe.restype = ctypes.c_int
    k32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                             ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    k32.ReadFile.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.restype = ctypes.c_int
    handle = k32.CreateFileW(pipe_name, 0xC0000000, 0, None, 3, 0, None)
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        raise OSError("CreateFileW failed")
    try:
        payload = (json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        written = ctypes.c_uint32()
        if not k32.WriteFile(handle, payload, len(payload), ctypes.byref(written), None):
            raise OSError("WriteFile failed")
        deadline = time.perf_counter() + max(1, timeout_ms) / 1000.0
        available = ctypes.c_uint32()
        while time.perf_counter() < deadline:
            if k32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None) and available.value:
                buffer = ctypes.create_string_buffer(available.value)
                read = ctypes.c_uint32()
                if not k32.ReadFile(handle, buffer, available.value, ctypes.byref(read), None):
                    raise OSError("ReadFile failed")
                response = loads_strict(buffer.raw[:read.value].decode("utf-8"))
                return validate_response(response, request)
            time.sleep(0.001)
        raise TimeoutError("ranker response timed out")
    finally:
        k32.CloseHandle(handle)
