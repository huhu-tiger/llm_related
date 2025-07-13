# SearXNG Docker 部署指南

## 关于 cap_drop 权限问题

### 问题描述
在 `docker-compose.yaml` 中，Redis 容器使用了 `cap_drop: - ALL` 来移除所有 Linux 能力，这会导致第一次启动时出现权限错误。

### 问题原因
1. `cap_drop: - ALL` 移除了容器的所有 Linux 能力
2. Redis/Valkey 容器第一次启动时需要创建数据目录和设置文件权限
3. 缺少必要的能力（如 `CHOWN`、`SETGID`、`SETUID`）导致初始化失败

### 解决方案

#### 方案1：使用初始化容器（推荐）
当前配置已经包含了一个 `redis-init` 容器，它会：
- 在 Redis 主容器启动前运行
- 以 root 用户身份创建数据目录
- 设置正确的文件权限和所有权
- 完成后自动退出

**优点：**
- 自动化解决权限问题
- 不需要手动干预
- 保持安全配置

#### 方案2：手动分阶段启动
如果遇到问题，可以临时注释掉 `cap_drop`：

```yaml
# 第一次启动时注释掉
# cap_drop:
#   - ALL

# 启动成功后，再启用
cap_drop:
  - ALL
```

#### 方案3：使用外部数据目录
```yaml
volumes:
  - ./redis-data:/data:rw  # 使用外部目录
```

### 启动步骤

1. **首次启动**：
   ```bash
   docker-compose up -d
   ```

2. **检查状态**：
   ```bash
   docker-compose ps
   docker-compose logs redis
   ```

3. **访问服务**：
   - SearXNG: http://localhost:8088
   - 确保 Redis 容器正常运行

### 故障排除

如果仍然遇到权限问题：

1. **清理数据卷**：
   ```bash
   docker-compose down -v
   docker volume rm searxng-docker_valkey-data2
   ```

2. **重新启动**：
   ```bash
   docker-compose up -d
   ```

3. **检查日志**：
   ```bash
   docker-compose logs redis-init
   docker-compose logs redis
   ```

### 安全说明

- `cap_drop: - ALL` 是重要的安全配置，移除不必要的权限
- 初始化容器只在启动时运行，不会持续存在
- 生产环境建议保持当前的安全配置 