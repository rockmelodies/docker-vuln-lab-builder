---
name: docker-vuln-lab-builder
description: 自动化构建Docker漏洞靶场容器，生成标准规范的环境。用于：(1) 构建Docker漏洞靶场镜像并运行容器，(2) 返回端口映射地址和访问地址，(3) 生成专业的漏洞靶场说明文档(Markdown)，(4) 将运行中的容器导出为tar包并返回路径，(5) 自动登录Docker Hub并推送镜像。当用户需要构建漏洞靶场、创建Docker安全实验环境、部署CTF题目、搭建漏洞练习环境时触发此Skill。
---

# Docker 漏洞靶场自动化构建

自动化构建标准化Docker漏洞靶场，涵盖构建、运行、文档生成、导出和推送全流程。

## 工作流程

按以下顺序执行，每步依赖前步结果：

1. **构建镜像** → 运行 `scripts/build_and_run.py` 构建并启动容器
2. **获取映射信息** → 脚本自动输出端口映射和访问地址
3. **生成靶场文档** → 基于 `references/vuln_doc_template.md` 模板生成说明文档
4. **导出容器** → 运行 `scripts/export_container.py` 导出tar包
5. **推送镜像** → 运行 `scripts/push_image.py` 推送到Docker Hub

## Step 1: 构建镜像并运行容器

```bash
python scripts/build_and_run.py --project-dir <项目目录> --image-name <镜像名> --ports <端口映射>
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--project-dir` | 是 | 包含Dockerfile的项目目录路径 |
| `--image-name` | 是 | 镜像名称，格式: `用户名/镜像名:标签` |
| `--ports` | 是 | 端口映射，格式: `宿主端口:容器端口`，多个用逗号分隔 |
| `--container-name` | 否 | 容器名称，默认自动生成 |
| `--env` | 否 | 环境变量，格式: `KEY=VALUE`，多个用逗号分隔 |
| `--privileged` | 否 | 是否特权模式运行，默认false |
| `--network` | 否 | 网络模式，默认bridge |
| `--volumes` | 否 | 挂载卷，格式: `宿主路径:容器路径`，多个用逗号分隔 |
| `--build-args` | 否 | 构建参数，格式: `KEY=VALUE`，多个用逗号分隔 |
| `--json-output` | 否 | 以JSON格式输出结果，便于脚本解析 |

### 输出示例

```
=== Docker 漏洞靶场构建结果 ===
镜像名称: rockmelodies/vuln-lab:latest
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

## Step 2: 生成靶场说明文档

基于 `references/vuln_doc_template.md` 模板，结合Step 1输出的映射信息，在项目目录下生成 `VULN_LAB_README.md`。

文档必须包含以下核心章节：
- 靶场概述（漏洞类型、难度等级、CVE编号）
- 环境信息（镜像、端口映射、访问地址）
- 漏洞描述与原理
- 漏洞利用步骤
- 修复建议
- 参考链接
- 免责声明

## Step 3: 导出容器为tar包

```bash
python scripts/export_container.py --container-name <容器名> --output-dir <输出目录>
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--container-name` | 是 | 容器名称或ID |
| `--output-dir` | 否 | tar包输出目录，默认 `./exports` |
| `--image-name` | 否 | 同时导出镜像（docker save），格式同image-name |
| `--json-output` | 否 | 以JSON格式输出结果 |

### 输出示例

```
=== 容器导出结果 ===
容器tar包路径: D:/vuln-labs/exports/vuln-lab-container-20260602.tar
镜像tar包路径: D:/vuln-labs/exports/vuln-lab-image-20260602.tar
容器tar包大小: 256.0MB
镜像tar包大小: 312.5MB
```

## Step 4: 推送镜像到Docker Hub

```bash
python scripts/push_image.py --image-name <镜像名> --username <用户名> --token <访问令牌>
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--image-name` | 是 | 镜像名称，格式: `用户名/镜像名:标签` |
| `--username` | 否 | Docker Hub用户名，默认: `rockmelodies` |
| `--token` | 否 | Docker Hub访问令牌，默认使用内置令牌 |
| `--registry` | 否 | 镜像仓库地址，默认: `docker.io` |
| `--source-image` | 否 | 源镜像名称（如需重新tag） |
| `--json-output` | 否 | 以JSON格式输出结果 |

### 输出示例

```
=== 镜像推送结果 ===
登录状态: Login Succeeded
推送镜像: rockmelodies/vuln-lab:latest
推送状态: Pushed
仓库地址: https://hub.docker.com/r/rockmelodies/vuln-lab
```

## Dockerfile 编写规范

编写Dockerfile时遵循以下规范，详见 `references/docker_best_practices.md`：

1. 基础镜像选择明确版本标签，禁止使用 `latest`
2. 非root用户运行应用（如应用允许）
3. 最小化安装，减少攻击面
4. 配置健康检查
5. 合理的镜像层缓存（合并RUN指令）
6. 敏感信息不硬编码，通过环境变量传入

## 模板文件

- Dockerfile模板: `assets/Dockerfile.template`
- docker-compose模板: `assets/docker-compose.template.yml`

## 参考文档

- 漏洞靶场文档模板: `references/vuln_doc_template.md`
- Docker最佳实践: `references/docker_best_practices.md`

## 注意事项

- 端口冲突时自动递增寻找可用端口
- 容器异常退出时自动输出日志便于排查
- 推送镜像前自动检查镜像是否已正确tag
- 导出tar包前检查磁盘空间是否充足
- 所有操作结果支持JSON格式输出，便于后续自动化处理
