<div align="center">

# 🐳 Docker Vuln Lab Builder

**自动化构建 Docker 漏洞靶场 · 一键部署 · 标准化输出**

[![Skill](https://img.shields.io/badge/Type-Copilot_Code_Skill-blue)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 简介

Docker Vuln Lab Builder 是一个 Copilot Code Skill，用于自动化构建标准化的 Docker 漏洞靶场环境。涵盖从镜像构建、容器运行、文档生成、容器导出到镜像推送的完整工作流，适用于安全研究、CTF 训练、漏洞复现等场景。

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🚀 **一键构建** | 自动构建 Docker 镜像并启动容器，返回端口映射和访问地址 |
| 📝 **文档生成** | 基于模板自动生成专业的漏洞靶场说明文档 (Markdown) |
| 📦 **容器导出** | 将运行中的容器/镜像导出为 tar 包，返回文件路径 |
| 🔄 **镜像推送** | 自动登录 Docker Hub 并推送镜像到远程仓库 |
| 🔌 **端口管理** | 自动检测端口冲突并递增寻找可用端口 |
| 📊 **结构化输出** | 支持 JSON 格式输出，便于自动化集成 |

---

## 🗂️ 目录结构

```
docker-vuln-lab-builder/
├── SKILL.md                              # Skill 主文件（触发条件 + 工作流程）
├── scripts/
│   ├── build_and_run.py                  # 构建镜像 + 运行容器 + 返回映射地址
│   ├── export_container.py               # 导出容器/镜像为 tar 包
│   └── push_image.py                     # 登录 Docker Hub 并推送镜像
├── references/
│   ├── vuln_doc_template.md              # 漏洞靶场说明文档模板
│   └── docker_best_practices.md          # Docker 最佳实践参考
└── assets/
    ├── Dockerfile.template               # Dockerfile 标准模板
    └── docker-compose.template.yml       # docker-compose 编排模板
```

---

## 🚀 快速开始

### 前置条件

- [Docker](https://www.docker.com/) 已安装并运行
- Python 3.8+

### 工作流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1. 构建镜像  │───▶│  2. 获取映射  │───▶│  3. 生成文档  │───▶│  4. 导出容器  │───▶│  5. 推送镜像  │
│  build & run │    │  端口 & 地址  │    │  VULN_LAB_   │    │  export tar  │    │  push to     │
│             │    │             │    │  README.md   │    │             │    │  Docker Hub  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Step 1: 构建镜像并运行容器

```bash
python scripts/build_and_run.py \
  --project-dir ./my-vuln-lab \
  --image-name rockmelodies/sqli-lab:latest \
  --ports 8080:80,3306:3306
```

**输出示例：**

```
=== Docker 漏洞靶场构建结果 ===
镜像名称: rockmelodies/sqli-lab:latest
容器ID: a1b2c3d4e5f6
容器名称: vuln-lab-a1b2c3
状态: running
端口映射:
  - 127.0.0.1:8080 → 容器端口 80/TCP (HTTP)
  - 127.0.0.1:3306 → 容器端口 3306/TCP (MySQL)
访问地址:
  - HTTP服务: http://127.0.0.1:8080
  - MySQL: mysql://127.0.0.1:3306
```

### Step 2: 生成靶场说明文档

基于 `references/vuln_doc_template.md` 模板，在项目目录下生成 `VULN_LAB_README.md`，包含：

- 🎯 靶场概述（漏洞类型、难度等级、CVE 编号）
- 🖥️ 环境信息（镜像、端口映射、访问地址）
- 🔍 漏洞描述与原理
- ⚔️ 漏洞利用步骤
- 🛡️ 修复建议
- 🔗 参考链接
- ⚖️ 免责声明

### Step 3: 导出容器为 tar 包

```bash
python scripts/export_container.py \
  --container-name vuln-lab-a1b2c3 \
  --output-dir ./exports
```

**输出示例：**

```
=== 容器导出结果 ===
容器tar包路径: D:/vuln-labs/exports/vuln-lab-a1b2c3-container-20260602.tar
镜像tar包路径: D:/vuln-labs/exports/rockmelodies_sqli-lab-image-20260602.tar
容器tar包大小: 256.0MB
镜像tar包大小: 312.5MB
```

### Step 4: 推送镜像到 Docker Hub

```bash
python scripts/push_image.py \
  --image-name rockmelodies/sqli-lab:latest
```

**输出示例：**

```
=== 镜像推送结果 ===
登录状态: Login Succeeded
推送镜像: rockmelodies/sqli-lab:latest
推送状态: Pushed
仓库地址: https://hub.docker.com/r/rockmelodies/sqli-lab
```

---

## 📚 脚本详细说明

### `build_and_run.py` — 构建与运行

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--project-dir` | ✅ | 包含 Dockerfile 的项目目录路径 |
| `--image-name` | ✅ | 镜像名称，格式: `用户名/镜像名:标签` |
| `--ports` | ✅ | 端口映射，格式: `宿主端口:容器端口`，多个用逗号分隔 |
| `--container-name` | ❌ | 容器名称，默认自动生成 |
| `--env` | ❌ | 环境变量，格式: `KEY=VALUE`，多个用逗号分隔 |
| `--privileged` | ❌ | 是否特权模式运行，默认 false |
| `--network` | ❌ | 网络模式，默认 bridge |
| `--volumes` | ❌ | 挂载卷，格式: `宿主路径:容器路径`，多个用逗号分隔 |
| `--build-args` | ❌ | 构建参数，格式: `KEY=VALUE`，多个用逗号分隔 |
| `--json-output` | ❌ | 以 JSON 格式输出结果 |

### `export_container.py` — 容器导出

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--container-name` | ✅ | 容器名称或 ID |
| `--output-dir` | ❌ | tar 包输出目录，默认 `./exports` |
| `--image-name` | ❌ | 同时导出镜像（docker save） |
| `--json-output` | ❌ | 以 JSON 格式输出结果 |

### `push_image.py` — 镜像推送

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `--image-name` | ✅ | 镜像名称，格式: `用户名/镜像名:标签` |
| `--username` | ❌ | Docker Hub 用户名，默认: `rockmelodies` |
| `--token` | ❌ | Docker Hub 访问令牌，默认使用内置令牌 |
| `--registry` | ❌ | 镜像仓库地址，默认: `docker.io` |
| `--source-image` | ❌ | 源镜像名称（如需重新 tag） |
| `--json-output` | ❌ | 以 JSON 格式输出结果 |

---

## 📋 模板文件

### Dockerfile 模板

位于 `assets/Dockerfile.template`，遵循以下规范：

- ✅ 基础镜像指定明确版本标签，禁止 `latest`
- ✅ 合并 RUN 指令减少镜像层
- ✅ 清理 apt 缓存
- ✅ 非root用户运行（如应用允许）
- ✅ 健康检查配置
- ✅ LABEL 元数据标注漏洞信息

### docker-compose 模板

位于 `assets/docker-compose.template.yml`，包含：

- Web 应用服务 + 数据库服务 + Redis 服务示例
- 健康检查配置
- 网络隔离
- 数据持久化
- 初始化脚本挂载

---

## 🔧 支持的漏洞靶场类型

| 漏洞类型 | 推荐基础镜像 | 典型端口 |
|----------|-------------|----------|
| SQL 注入 | `php:8.1-apache` | 80, 3306 |
| XSS | 任意 Web 框架 | 80 |
| 文件上传 | `php:8.1-apache` | 80 |
| 反序列化 (Java) | `openjdk:11-jdk-slim` | 80, 1099 |
| 反序列化 (Python) | `python:3.10-slim` | 80 |
| SSRF | `python:3.10-slim` | 80 |
| 命令注入 | `ubuntu:22.04` | 80 |
| 提权 | `ubuntu:22.04` | 22 |
| 容器逃逸 | `ubuntu:22.04` (特权) | 22, 80 |

---

## ⚠️ 注意事项

- 端口冲突时自动递增寻找可用端口
- 容器异常退出时自动输出日志便于排查
- 推送镜像前自动检查镜像是否已正确 tag
- 导出 tar 包前检查磁盘空间是否充足
- 所有脚本支持 `--json-output` 参数输出结构化 JSON 数据

---

## 📄 许可证

本项目仅供安全研究和授权测试使用。使用者须遵守当地法律法规，未经授权对他人系统进行测试属于违法行为。

<div align="center">

**Made with ❤️ for Security Research**

</div>
