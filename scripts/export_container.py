#!/usr/bin/env python3
"""
Docker 容器导出脚本
将运行中的容器导出为tar包，同时可选导出镜像
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Tuple


def run_command(cmd: str, check: bool = True, capture: bool = True) -> Tuple[int, str, str]:
    """执行shell命令并返回结果"""
    print(f"[CMD] {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, encoding='utf-8', errors='replace'
    )
    if check and result.returncode != 0:
        print(f"[ERROR] 命令执行失败: {cmd}")
        print(f"[STDERR] {result.stderr}")
        sys.exit(1)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_container_exists(container_name: str) -> bool:
    """检查容器是否存在"""
    code, stdout, _ = run_command(
        f"docker inspect --format '{{{{.Id}}}}' {container_name}", check=False
    )
    return code == 0


def get_container_status(container_name: str) -> str:
    """获取容器状态"""
    code, stdout, _ = run_command(
        f"docker inspect --format '{{{{.State.Status}}}}' {container_name}", check=False
    )
    return stdout.strip() if code == 0 else "unknown"


def get_container_image(container_name: str) -> str:
    """获取容器使用的镜像名称"""
    code, stdout, _ = run_command(
        f"docker inspect --format '{{{{.Config.Image}}}}' {container_name}", check=False
    )
    return stdout.strip() if code == 0 else ""


def check_disk_space(output_dir: str, required_mb: int = 500) -> bool:
    """检查磁盘空间是否充足"""
    try:
        if sys.platform == 'win32':
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.path.dirname(os.path.abspath(output_dir))),
                None, None, ctypes.pointer(free_bytes)
            )
            free_mb = free_bytes.value / (1024 * 1024)
        else:
            stat = os.statvfs(os.path.dirname(os.path.abspath(output_dir)))
            free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

        if free_mb < required_mb:
            print(f"[WARN] 磁盘剩余空间不足: {free_mb:.0f}MB < {required_mb}MB")
            return False
        return True
    except Exception as e:
        print(f"[WARN] 无法检查磁盘空间: {e}")
        return True  # 无法检查时继续执行


def export_container(container_name: str, output_dir: str) -> str:
    """导出容器为tar包"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tar_path = os.path.join(output_dir, f"{container_name}-container-{timestamp}.tar")

    print(f"[INFO] 导出容器: {container_name} → {tar_path}")
    code, _, stderr = run_command(
        f"docker export -o \"{tar_path}\" {container_name}", check=False
    )
    if code != 0:
        print(f"[ERROR] 容器导出失败: {stderr}")
        sys.exit(1)

    if not os.path.exists(tar_path):
        print(f"[ERROR] 导出文件未生成: {tar_path}")
        sys.exit(1)

    size_mb = os.path.getsize(tar_path) / (1024 * 1024)
    print(f"[INFO] 容器导出成功: {tar_path} ({size_mb:.1f}MB)")
    return tar_path


def export_image(image_name: str, output_dir: str) -> str:
    """导出镜像为tar包"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 清理镜像名中的特殊字符
    safe_name = image_name.replace('/', '_').replace(':', '_')
    tar_path = os.path.join(output_dir, f"{safe_name}-image-{timestamp}.tar")

    print(f"[INFO] 导出镜像: {image_name} → {tar_path}")
    code, _, stderr = run_command(
        f"docker save -o \"{tar_path}\" {image_name}", check=False
    )
    if code != 0:
        print(f"[ERROR] 镜像导出失败: {stderr}")
        sys.exit(1)

    if not os.path.exists(tar_path):
        print(f"[ERROR] 导出文件未生成: {tar_path}")
        sys.exit(1)

    size_mb = os.path.getsize(tar_path) / (1024 * 1024)
    print(f"[INFO] 镜像导出成功: {tar_path} ({size_mb:.1f}MB)")
    return tar_path


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def main():
    parser = argparse.ArgumentParser(description='Docker容器导出脚本')
    parser.add_argument('--container-name', required=True, help='容器名称或ID')
    parser.add_argument('--output-dir', default='./exports', help='tar包输出目录 (默认: ./exports)')
    parser.add_argument('--image-name', default=None, help='同时导出镜像 (格式: 用户名/镜像名:标签)')
    parser.add_argument('--json-output', action='store_true', help='以JSON格式输出结果')

    args = parser.parse_args()

    # 检查容器是否存在
    if not check_container_exists(args.container_name):
        print(f"[ERROR] 容器不存在: {args.container_name}")
        sys.exit(1)

    # 检查磁盘空间
    check_disk_space(args.output_dir)

    # 获取容器信息
    status = get_container_status(args.container_name)
    image = get_container_image(args.container_name)

    print(f"[INFO] 容器状态: {status}")
    print(f"[INFO] 容器镜像: {image}")

    # 导出容器
    container_tar = export_container(args.container_name, args.output_dir)
    container_size = os.path.getsize(container_tar)

    result = {
        'container_name': args.container_name,
        'container_status': status,
        'container_image': image,
        'container_tar_path': os.path.abspath(container_tar),
        'container_tar_size': format_file_size(container_size),
    }

    # 可选：导出镜像
    if args.image_name:
        image_tar = export_image(args.image_name, args.output_dir)
        image_size = os.path.getsize(image_tar)
        result['image_name'] = args.image_name
        result['image_tar_path'] = os.path.abspath(image_tar)
        result['image_tar_size'] = format_file_size(image_size)
    elif image:
        # 自动使用容器镜像名导出
        image_tar = export_image(image, args.output_dir)
        image_size = os.path.getsize(image_tar)
        result['image_name'] = image
        result['image_tar_path'] = os.path.abspath(image_tar)
        result['image_tar_size'] = format_file_size(image_size)

    # 输出结果
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n=== 容器导出结果 ===")
        print(f"容器tar包路径: {result['container_tar_path']}")
        print(f"容器tar包大小: {result['container_tar_size']}")
        if 'image_tar_path' in result:
            print(f"镜像tar包路径: {result['image_tar_path']}")
            print(f"镜像tar包大小: {result['image_tar_size']}")


if __name__ == '__main__':
    main()
