# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# 增加递归限制
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# 收集 RapidOCR 数据文件
import rapidocr_onnxruntime
rapidocr_path = os.path.dirname(rapidocr_onnxruntime.__file__)

datas = []
# 添加 RapidOCR 所有文件
for root, dirs, files in os.walk(rapidocr_path):
    for file in files:
        src = os.path.join(root, file)
        rel_path = os.path.relpath(root, os.path.dirname(rapidocr_path))
        datas.append((src, rel_path))

print(f"RapidOCR 数据文件: {len(datas)} 个")

# 添加 jieba 词典
import jieba
jieba_path = os.path.dirname(jieba.__file__)
for root, dirs, files in os.walk(jieba_path):
    for file in files:
        if file.endswith('.txt'):
            src = os.path.join(root, file)
            rel_path = os.path.relpath(root, os.path.dirname(jieba_path))
            datas.append((src, rel_path))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'rapidocr_onnxruntime',
        'rapidocr_onnxruntime.ch_ppocr_mobile_v2',
        'jieba',
        'jieba.posseg',
        'fuzzywuzzy',
        'fuzzywuzzy.fuzz',
        'fuzzywuzzy.process',
        'cv2',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'PIL.ImageTk',
        'pandas',
        'openpyxl',
        'openpyxl.cell',
        'sqlite3',
        'pyautogui',
        'pyscreeze',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'onnxruntime',
        'onnxruntime.capi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'tensorboard', 'tensorflow',
        'matplotlib', 'IPython', 'jupyter', 'notebook', 'scipy',
        'paddle', 'paddleocr', 'paddlex', 'ppocr',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='阴阳师答题助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='阴阳师答题助手',
)
