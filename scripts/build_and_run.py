#!/usr/bin/env python3
"""
Docker 漏洞靶场构建与运行脚本
自动构建Docker镜像、启动容器、返回端口映射和访问地址
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple


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


def check_docker_available() -> bool:
    """检查Docker是否可用"""
    code, _, _ = run_command("docker --version", check=False)
    if code != 0:
        print("[ERROR] Docker未安装或未启动，请先安装并启动Docker")
        sys.exit(1)
    return True


def find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """寻找可用端口"""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    print(f"[ERROR] 在端口范围 {start_port}-{start_port + max_attempts} 内未找到可用端口")
    sys.exit(1)


def parse_port_mappings(ports_str: str) -> List[Dict]:
    """解析端口映射字符串"""
    mappings = []
    for mapping in ports_str.split(','):
        mapping = mapping.strip()
        if ':' in mapping:
            host_port, container_port = mapping.split(':', 1)
            # 提取协议和端口号
            protocol = "TCP"
            port_num = container_port
            if '/' in port_num:
                port_num, protocol = port_num.rsplit('/', 1)
                protocol = protocol.upper()
            mappings.append({
                'host_port': int(host_port),
                'container_port': int(port_num),
                'protocol': protocol
            })
        else:
            mappings.append({
                'host_port': int(mapping),
                'container_port': int(mapping),
                'protocol': 'TCP'
            })
    return mappings


def resolve_port_conflicts(mappings: List[Dict]) -> List[Dict]:
    """检测并解决端口冲突"""
    resolved = []
    for m in mappings:
        host_port = find_available_port(m['host_port'])
        m['host_port'] = host_port
        resolved.append(m)
    return resolved


def get_service_name(port: int) -> str:
    """根据端口号推断服务名称"""
    service_map = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
        1433: "MSSQL", 1521: "Oracle", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5672: "RabbitMQ",
        6379: "Redis", 8080: "HTTP", 8443: "HTTPS",
        8888: "HTTP", 9000: "PHP-FPM", 9090: "Prometheus",
        27017: "MongoDB", 11211: "Memcached",
    }
    return service_map.get(port, "Unknown")


def build_image(project_dir: str, image_name: str, build_args: Optional[str] = None) -> bool:
    """构建Docker镜像"""
    dockerfile_path = os.path.join(project_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        print(f"[ERROR] Dockerfile不存在: {dockerfile_path}")
        sys.exit(1)

    cmd = f"docker build -t {image_name} {project_dir}"
    if build_args:
        for arg in build_args.split(','):
            arg = arg.strip()
            cmd += f" --build-arg {arg}"

    print(f"[INFO] 开始构建镜像: {image_name}")
    code, stdout, stderr = run_command(cmd, check=False, capture=True)
    if code != 0:
        print(f"[ERROR] 镜像构建失败")
        print(stderr)
        sys.exit(1)
    print(f"[INFO] 镜像构建成功: {image_name}")
    return True


def run_container(
    image_name: str,
    port_mappings: List[Dict],
    container_name: Optional[str] = None,
    env_vars: Optional[str] = None,
    privileged: bool = False,
    network: str = "bridge",
    volumes: Optional[str] = None,
) -> Dict:
    """运行Docker容器"""
    if not container_name:
        container_name = f"vuln-lab-{uuid.uuid4().hex[:8]}"

    # 构建端口映射参数
    port_args = ""
    for m in port_mappings:
        port_args += f" -p {m['host_port']}:{m['container_port']}/{m['protocol'].lower()}"

    # 构建环境变量参数
    env_args = ""
    if env_vars:
        for env in env_vars.split(','):
            env = env.strip()
            env_args += f" -e {env}"

    # 构建挂载卷参数
    vol_args = ""
    if volumes:
        for vol in volumes.split(','):
            vol = vol.strip()
            vol_args += f" -v {vol}"

    # 特权模式
    priv_args = " --privileged" if privileged else ""

    cmd = (
        f"docker run -d --name {container_name}"
        f"{port_args}{env_args}{vol_args}{priv_args}"
        f" --network {network}"
        f" {image_name}"
    )

    print(f"[INFO] 启动容器: {container_name}")
    code, stdout, stderr = run_command(cmd, check=False)
    if code != 0:
        print(f"[ERROR] 容器启动失败")
        print(stderr)
        sys.exit(1)

    container_id = stdout[:12]
    print(f"[INFO] 容器启动成功: {container_id}")

    # 等待容器启动并检查状态
    import time
    time.sleep(2)
    code, status, _ = run_command(
        f"docker inspect --format '{{{{.State.Status}}}}' {container_name}", check=False
    )

    return {
        'container_id': container_id,
        'container_name': container_name,
        'status': status if code == 0 else 'unknown',
        'image_name': image_name,
    }


def get_container_logs(container_name: str, lines: int = 50) -> str:
    """获取容器日志"""
    _, logs, _ = run_command(f"docker logs --tail {lines} {container_name}", check=False)
    return logs


def format_output(result: Dict, port_mappings: List[Dict]) -> str:
    """格式化输出结果"""
    output_lines = [
        "=== Docker 漏洞靶场构建结果 ===",
        f"镜像名称: {result['image_name']}",
        f"容器ID: {result['container_id']}",
        f"容器名称: {result['container_name']}",
        f"状态: {result['status']}",
        "",
        "端口映射:",
    ]

    for m in port_mappings:
        service = get_service_name(m['container_port'])
        protocol = m['protocol']
        output_lines.append(
            f"  - 127.0.0.1:{m['host_port']} → 容器端口 {m['container_port']}/{protocol} ({service})"
        )

    output_lines.append("")
    output_lines.append("访问地址:")

    for m in port_mappings:
        service = get_service_name(m['container_port'])
        if m['container_port'] in (80, 8080, 8888, 9000):
            output_lines.append(f"  - {service}服务: http://127.0.0.1:{m['host_port']}")
        elif m['container_port'] in (443, 8443):
            output_lines.append(f"  - {service}服务: https://127.0.0.1:{m['host_port']}")
        elif m['container_port'] == 3306:
            output_lines.append(f"  - {service}: mysql://127.0.0.1:{m['host_port']}")
        elif m['container_port'] == 5432:
            output_lines.append(f"  - {service}: postgresql://127.0.0.1:{m['host_port']}")
        elif m['container_port'] == 6379:
            output_lines.append(f"  - {service}: redis://127.0.0.1:{m['host_port']}")
        elif m['container_port'] == 27017:
            output_lines.append(f"  - {service}: mongodb://127.0.0.1:{m['host_port']}")
        elif m['container_port'] == 22:
            output_lines.append(f"  - {service}: ssh://127.0.0.1:{m['host_port']}")
        else:
            output_lines.append(f"  - {service}: 127.0.0.1:{m['host_port']}")

    return '\n'.join(output_lines)


def main():
    parser = argparse.ArgumentParser(description='Docker漏洞靶场构建与运行脚本')
    parser.add_argument('--project-dir', required=True, help='包含Dockerfile的项目目录路径')
    parser.add_argument('--image-name', required=True, help='镜像名称 (格式: 用户名/镜像名:标签)')
    parser.add_argument('--ports', required=True, help='端口映射 (格式: 宿主端口:容器端口, 多个用逗号分隔)')
    parser.add_argument('--container-name', default=None, help='容器名称 (默认自动生成)')
    parser.add_argument('--env', default=None, help='环境变量 (格式: KEY=VALUE, 多个用逗号分隔)')
    parser.add_argument('--privileged', action='store_true', help='是否特权模式运行')
    parser.add_argument('--network', default='bridge', help='网络模式 (默认: bridge)')
    parser.add_argument('--volumes', default=None, help='挂载卷 (格式: 宿主路径:容器路径, 多个用逗号分隔)')
    parser.add_argument('--build-args', default=None, help='构建参数 (格式: KEY=VALUE, 多个用逗号分隔)')
    parser.add_argument('--json-output', action='store_true', help='以JSON格式输出结果')

    args = parser.parse_args()

    # 检查Docker可用性
    check_docker_available()

    # 解析端口映射
    port_mappings = parse_port_mappings(args.ports)

    # 解决端口冲突
    port_mappings = resolve_port_conflicts(port_mappings)

    # 构建镜像
    build_image(args.project_dir, args.image_name, args.build_args)

    # 运行容器
    result = run_container(
        image_name=args.image_name,
        port_mappings=port_mappings,
        container_name=args.container_name,
        env_vars=args.env,
        privileged=args.privileged,
        network=args.network,
        volumes=args.volumes,
    )

    # 如果容器异常退出，输出日志
    if result['status'] != 'running':
        print(f"[WARN] 容器状态异常: {result['status']}")
        logs = get_container_logs(result['container_name'])
        print(f"[容器日志]:\n{logs}")

    # 输出结果
    if args.json_output:
        result['port_mappings'] = port_mappings
        # 构建访问地址列表
        access_urls = []
        for m in port_mappings:
            service = get_service_name(m['container_port'])
            access_urls.append({
                'service': service,
                'host_port': m['host_port'],
                'container_port': m['container_port'],
                'protocol': m['protocol'],
                'url': f"127.0.0.1:{m['host_port']}"
            })
        result['access_urls'] = access_urls
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_output(result, port_mappings))


if __name__ == '__main__':
    main()
