# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

ROOT = Path(os.path.abspath(".")).resolve()

block_cipher = None

all_datas = [
    ('build/onnx-model/ruri-ime-fp16.onnx', 'models/onnx'),
    ('build/onnx-model/ruri-ime-int8.onnx', 'models/onnx'),
    ('models/ruri-v3-reranker-310m-ime-tuned/tokenizer.json', 'models/onnx'),
    ('data/massive_homophone_database.json', 'data'),
    ('PRIVACY.md', 'documents'),
    ('LICENSE', 'documents'),
    ('NOTICE', 'documents'),
    ('THIRD_PARTY_LICENSES.md', 'documents'),
    ('docs/SYSTEM_REQUIREMENTS_JA.md', 'documents'),
    ('docs/README_DISTRIBUTION_JA.md', 'documents'),
]

all_hidden = [
    'pystray',
    'pystray._win32',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'numpy',
    'onnxruntime',
    'onnxruntime.capi._pybind_state',
    'tokenizers',
    'product_settings',
    'settings_ui',
    'onboarding_ui',
    'ranker.ranker',
    'ranker.onnx_ranker',
    'ranker.lexicon',
    'ranker.protocol',
    'ranker.loading_ui',
    'client.windows_pipe',
]

a = Analysis(
    ['ai_ime_tray.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'transformers', 'matplotlib', 'scipy', 'pandas', 'nltk', 'pygame',
        'diffusers', 'yt_dlp', 'librosa', 'datasets', 'pyarrow', 'sqlalchemy',
        'uvicorn', 'fastapi', 'starlette', 'rich', 'optuna', 'lightning',
        'aiohttp', 'aiofiles', 'gradio', 'gradio_client', 'openai', 'typer',
        'soundfile', 'torchaudio', 'torchvision', 'trio', 'anyio', 'httpx', 'httpcore',
        'peft', 'tensorboard', 'huggingface_hub', 'requests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YamatanaAIIME',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    version=str(ROOT / 'scripts' / 'version_info.txt'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='YamatanaAIIME',
)
