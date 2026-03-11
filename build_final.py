"""
打包脚本 - 使用 PyInstaller 打包阴阳师答题助手
使用方法: python build_final.py
"""
import os
import sys
import subprocess
import shutil

def clean():
    """清理之前的构建"""
    print("清理之前的构建...")
    for path in ['build', 'dist']:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            print(f"  已删除: {path}")
    print("✓ 清理完成")

def build():
    """执行打包"""
    print("\n开始打包...")
    print("=" * 60)
    
    # 使用spec文件打包
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'yys_assistant.spec',
        '--clean',
        '--noconfirm'
    ]
    
    print(f"执行命令: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n" + "=" * 60)
        print("✓ 打包成功!")
        print("=" * 60)
        print(f"\n输出目录: dist/阴阳师答题助手/")
        print("\n请检查以下文件是否存在:")
        print("  - dist/阴阳师答题助手/阴阳师答题助手.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        return False

def main():
    print("=" * 60)
    print("阴阳师答题助手 - 打包工具")
    print("=" * 60)
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✓ PyInstaller 安装完成")
    
    # 清理
    clean()
    
    # 打包
    if build():
        print("\n" + "=" * 60)
        print("打包完成! 请测试运行 dist/阴阳师答题助手/阴阳师答题助手.exe")
        print("=" * 60)
    else:
        print("\n打包失败，请查看错误信息")
        sys.exit(1)

if __name__ == '__main__':
    main()
