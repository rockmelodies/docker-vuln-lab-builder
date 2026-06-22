# Docker 漏洞靶场最佳实践

## 目录

1. [基础镜像选择](#1-基础镜像选择)
2. [Dockerfile编写规范](#2-dockerfile编写规范)
3. [安全加固](#3-安全加固)
4. [端口与服务配置](#4-端口与服务配置)
5. [多服务编排](#5-多服务编排)
6. [常见漏洞靶场类型](#6-常见漏洞靶场类型)
7. [调试与排错](#7-调试与排错)

---

## 1. 基础镜像选择

### 按漏洞类型选择

| 漏洞类型 | 推荐基础镜像 | 说明 |
|----------|-------------|------|
| Web注入(SQLi/XSS) | `php:8.1-apache`, `python:3.10-slim` | 含Web服务器 |
| 文件上传 | `php:8.1-apache` | PHP文件处理 |
| 反序列化(Java) | `openjdk:11-jdk-slim` | Java环境 |
| 反序列化(Python) | `python:3.10-slim` | pickle/yaml等 |
| SSRF | `python:3.10-slim`, `node:18-alpine` | HTTP客户端 |
| RCE | `ubuntu:22.04`, `debian:bullseye` | 命令执行环境 |
| 提权 | `ubuntu:22.04` | SUID/Capabilities |
| 容器逃逸 | `ubuntu:22.04` | 需特权模式 |
| 中间件漏洞 | 对应中间件官方镜像 | Tomcat/WebLogic等 |

### 镜像大小优化

- 优先使用 `-slim` 或 `-alpine` 变体
- 生产靶场镜像建议控制在 500MB 以内
- 使用多阶段构建减小最终镜像大小

---

## 2. Dockerfile编写规范

### 必须遵守

```dockerfile
# ✅ 指定明确版本标签
FROM ubuntu:22.04

# ❌ 禁止使用latest
# FROM ubuntu:latest
```

```dockerfile
# ✅ 合并RUN指令减少镜像层
RUN apt-get update && apt-get install -y \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*

# ❌ 每个包单独RUN
# RUN apt-get update
# RUN apt-get install -y package1
# RUN apt-get install -y package2
```

```dockerfile
# ✅ 清理缓存
RUN apt-get update && apt-get install -y ... \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
```

### 建议遵守

- 使用 `.dockerignore` 排除无关文件
- COPY指令使用通配符而非整个目录
- 设置合理的 WORKDIR
- 使用 LABEL 添加元数据

---

## 3. 安全加固

### 靶场特殊考虑

漏洞靶场本身包含已知漏洞，但仍需基础安全措施：

1. **网络隔离**: 使用自定义bridge网络，不使用host网络
2. **资源限制**: 设置内存和CPU限制防止资源耗尽
3. **只读文件系统**: 非必要目录设为只读
4. **最小权限**: 仅在需要时使用 `--privileged` 或 `cap_add`

### 资源限制示例

```bash
docker run -d \
  --memory="512m" \
  --cpus="1.0" \
  --pids-limit=100 \
  --read-only \
  --tmpfs /tmp:size=100m \
  --tmpfs /run:size=50m \
  -p 8080:80 \
  vuln-lab:latest
```

### 特权模式使用场景

仅在以下场景使用 `--privileged`：
- 容器逃逸靶场
- 需要访问 `/proc` 或 `/sys` 的靶场
- 需要加载内核模块的靶场

---

## 4. 端口与服务配置

### 常用端口映射

| 服务 | 容器端口 | 建议宿主端口 | 说明 |
|------|----------|-------------|------|
| HTTP | 80 | 8080+ | Web应用 |
| HTTPS | 443 | 8443+ | 加密Web |
| MySQL | 3306 | 3306+ | 数据库 |
| PostgreSQL | 5432 | 5432+ | 数据库 |
| Redis | 6379 | 6379+ | 缓存 |
| SSH | 22 | 2222+ | 远程访问 |
| FTP | 21 | 2121+ | 文件传输 |

### 健康检查配置

```dockerfile
# HTTP服务
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# MySQL
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD mysqladmin ping -h localhost || exit 1

# 自定义脚本
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD /app/healthcheck.sh || exit 1
```

---

## 5. 多服务编排

### docker-compose 使用场景

当靶场需要多个服务协同工作时使用 docker-compose：
- Web应用 + 数据库
- 前端 + 后端API
- 应用 + 缓存 + 数据库

### 初始化顺序控制

```yaml
depends_on:
  db:
    condition: service_healthy
  redis:
    condition: service_started
```

### 数据库初始化

MySQL: 将SQL文件放入 `/docker-entrypoint-initdb.d/`
PostgreSQL: 将SQL/Shell脚本放入 `/docker-entrypoint-initdb.d/`

---

## 6. 常见漏洞靶场类型

### SQL注入靶场

```
技术栈: PHP + MySQL / Python + SQLite
关键文件: 带有拼接SQL的查询代码
端口: 80(HTTP) + 3306(MySQL)
```

### XSS靶场

```
技术栈: 任意Web框架
关键文件: 未转义输出的模板
端口: 80(HTTP)
```

### 文件上传靶场

```
技术栈: PHP / JSP / ASP.NET
关键文件: 无过滤的上传处理代码
端口: 80(HTTP)
```

### 反序列化靶场

```
技术栈: Java(commons-collections) / Python(pickle)
关键文件: 反序列化入口点
端口: 80(HTTP) 或 1099(RMI)
```

### SSRF靶场

```
技术栈: Python(requests) / Node.js(axios)
关键文件: 接受URL参数的请求转发代码
端口: 80(HTTP)
```

### 命令注入靶场

```
技术栈: 任意后端语言
关键文件: 调用系统命令的代码
端口: 80(HTTP)
```

---

## 7. 调试与排错

### 容器无法启动

```bash
# 查看容器日志
docker logs <container_name>

# 查看退出码
docker inspect --format '{{.State.ExitCode}}' <container_name>

# 交互式进入容器调试
docker run -it --entrypoint /bin/bash <image_name>
```

### 常见退出码

| 退出码 | 含义 | 解决方案 |
|--------|------|----------|
| 0 | 正常退出 | 检查CMD是否为前台进程 |
| 1 | 应用错误 | 查看应用日志 |
| 137 | OOM Killed | 增加内存限制 |
| 139 | Segfault | 检查应用兼容性 |

### 端口冲突

```bash
# Windows查看端口占用
netstat -ano | findstr :8080

# Linux/Mac查看端口占用
lsof -i :8080
ss -tlnp | grep 8080
```

### 镜像构建失败

```bash
# 不使用缓存重新构建
docker build --no-cache -t <image_name> .

# 查看构建历史
docker history <image_name>
```
