"""
分卷压缩工具 - 将大文件分割成多个小文件
"""
import os
import sys

def split_file(filename, chunk_size=90*1024*1024):  # 90MB per file
    """分割文件"""
    if not os.path.exists(filename):
        print(f"Error: File not found {filename}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Files in directory: {os.listdir('.')}")
        return
    
    file_size = os.path.getsize(filename)
    print(f"Original file size: {file_size / 1024 / 1024:.2f} MB")
    print(f"Chunk size: {chunk_size / 1024 / 1024:.0f} MB")
    print(f"Splitting file...")
    
    part_num = 1
    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            part_filename = f"{filename}.{part_num:02d}"
            with open(part_filename, 'wb') as part_file:
                part_file.write(chunk)
            
            part_size = len(chunk) / 1024 / 1024
            print(f"Created: {os.path.basename(part_filename)} ({part_size:.2f} MB)")
            part_num += 1
    
    print(f"\nDone! Total {part_num - 1} parts")
    print("Upload all .zip.01, .zip.02 files to Gitee")
    print("Users need to download all parts and use 7-Zip or WinRAR to extract")

if __name__ == '__main__':
    zip_file = r'阴阳师答题助手-win64-v1.0.zip'
    if len(sys.argv) > 1:
        zip_file = sys.argv[1]
    
    split_file(zip_file)
