#!/usr/bin/env python3
"""
Docker 镜像推送脚本
自动登录Docker Hub并推送镜像到远程仓库
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Tuple


# 默认凭证
DEFAULT_USERNAME = "rockmelodies"
DEFAULT_TOKEN = os.getenv("DOCKER_PAT", "")
DEFAULT_REGISTRY = "docker.io"


def run_command(cmd: str, check: bool = True, capture: bool = True, stdin_data: str = None) -> Tuple[int, str, str]:
    """执行shell命令并返回结果"""
    print(f"[CMD] {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True,
        encoding='utf-8', errors='replace', input=stdin_data
    )
    if check and result.returncode != 0:
        print(f"[ERROR] 命令执行失败: {cmd}")
        print(f"[STDERR] {result.stderr}")
        sys.exit(1)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def docker_login(username: str, token: str, registry: str = DEFAULT_REGISTRY) -> bool:
    """登录Docker Hub"""
    print(f"[INFO] 登录Docker仓库: {registry} (用户: {username})")

    # 使用echo传递token到docker login的stdin
    if registry == DEFAULT_REGISTRY:
        cmd = f"echo {token} | docker login -u {username} --password-stdin"
    else:
        cmd = f"echo {token} | docker login {registry} -u {username} --password-stdin"

    code, stdout, stderr = run_command(cmd, check=False)
    if code != 0:
        print(f"[ERROR] Docker登录失败")
        print(f"[STDERR] {stderr}")
        sys.exit(1)

    if "Login Succeeded" in stdout or "Login Succeeded" in stderr:
        print("[INFO] Docker登录成功")
        return True
    else:
        print(f"[WARN] 登录结果未确认: {stdout} {stderr}")
        return True  # 继续执行


def check_image_exists(image_name: str) -> bool:
    """检查本地镜像是否存在"""
    code, stdout, _ = run_command(f"docker image inspect {image_name}", check=False)
    return code == 0


def tag_image(source_image: str, target_image: str) -> bool:
    """为镜像打标签"""
    print(f"[INFO] 标记镜像: {source_image} → {target_image}")
    code, _, stderr = run_command(f"docker tag {source_image} {target_image}", check=False)
    if code != 0:
        print(f"[ERROR] 镜像标记失败: {stderr}")
        sys.exit(1)
    return True


def push_image(image_name: str) -> bool:
    """推送镜像到远程仓库"""
    print(f"[INFO] 推送镜像: {image_name}")
    code, stdout, stderr = run_command(f"docker push {image_name}", check=False)
    if code != 0:
        print(f"[ERROR] 镜像推送失败")
        print(f"[STDERR] {stderr}")
        sys.exit(1)

    # 检查推送结果
    output = stdout + stderr
    if "Pushed" in output or "already exists" in output or "digest" in output.lower():
        print(f"[INFO] 镜像推送成功: {image_name}")
        return True
    else:
        print(f"[WARN] 推送结果未确认，请手动检查")
        return True


def get_image_info(image_name: str) -> dict:
    """获取镜像详细信息"""
    code, stdout, _ = run_command(
        f"docker inspect --format '{{{{json .}}}}' {image_name}", check=False
    )
    if code == 0:
        try:
            info = json.loads(stdout)
            if isinstance(info, list):
                info = info[0]
            return {
                'size_mb': round(info.get('Size', 0) / (1024 * 1024), 1),
                'created': info.get('Created', ''),
                'os': info.get('Os', ''),
                'architecture': info.get('Architecture', ''),
            }
        except json.JSONDecodeError:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description='Docker镜像推送脚本')
    parser.add_argument('--image-name', required=True, help='镜像名称 (格式: 用户名/镜像名:标签)')
    parser.add_argument('--username', default=DEFAULT_USERNAME, help=f'Docker Hub用户名 (默认: {DEFAULT_USERNAME})')
    parser.add_argument('--token', default=DEFAULT_TOKEN, help='Docker Hub访问令牌 (默认从环境变量 DOCKER_PAT 读取)')
    parser.add_argument('--registry', default=DEFAULT_REGISTRY, help=f'镜像仓库地址 (默认: {DEFAULT_REGISTRY})')
    parser.add_argument('--source-image', default=None, help='源镜像名称 (如需重新tag)')
    parser.add_argument('--json-output', action='store_true', help='以JSON格式输出结果')

    args = parser.parse_args()

    # 检查 token 是否已提供
    if not args.token:
        print("[ERROR] 未提供 Docker Hub 访问令牌。请设置环境变量 DOCKER_PAT 或通过 --token 参数传入。")
        sys.exit(1)

    # 检查镜像是否存在
    image_to_push = args.image_name
    if args.source_image:
        if not check_image_exists(args.source_image):
            print(f"[ERROR] 源镜像不存在: {args.source_image}")
            sys.exit(1)
        tag_image(args.source_image, args.image_name)
    else:
        if not check_image_exists(args.image_name):
            print(f"[ERROR] 镜像不存在: {args.image_name}")
            sys.exit(1)

    # 登录Docker Hub
    login_success = docker_login(args.username, args.token, args.registry)

    # 推送镜像
    push_success = push_image(args.image_name)

    # 获取镜像信息
    image_info = get_image_info(args.image_name)

    # 构建仓库URL
    # 从image_name提取用户名和镜像名
    parts = args.image_name.split('/')
    if len(parts) >= 2:
        repo_url = f"https://hub.docker.com/r/{parts[0]}/{parts[1].split(':')[0]}"
    else:
        repo_url = f"https://hub.docker.com/r/{args.image_name.split(':')[0]}"

    result = {
        'login_status': 'Login Succeeded' if login_success else 'Login Failed',
        'pushed_image': args.image_name,
        'push_status': 'Pushed' if push_success else 'Failed',
        'repository_url': repo_url,
        'image_info': image_info,
    }

    # 输出结果
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n=== 镜像推送结果 ===")
        print(f"登录状态: {result['login_status']}")
        print(f"推送镜像: {result['pushed_image']}")
        print(f"推送状态: {result['push_status']}")
        print(f"仓库地址: {result['repository_url']}")
        if image_info:
            print(f"镜像大小: {image_info.get('size_mb', 'N/A')}MB")
            print(f"操作系统: {image_info.get('os', 'N/A')}")
            print(f"架构: {image_info.get('architecture', 'N/A')}")


if __name__ == '__main__':
    main()
