# CN5-Lite 部署指南

## 📋 目录

- [环境要求](#环境要求)
- [本地部署](#本地部署)
- [Docker部署](#docker部署)
- [生产环境部署](#生产环境部署)
- [性能优化](#性能优化)
- [监控和日志](#监控和日志)
- [备份和恢复](#备份和恢复)
- [故障排除](#故障排除)

---

## 环境要求

### 硬件要求

**最小配置**:
- CPU: 2核心
- 内存: 4GB
- 磁盘: 20GB

**推荐配置**:
- CPU: 4核心以上
- 内存: 8GB以上
- 磁盘: 50GB以上（SSD）

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+) / macOS / Windows 10+
- **Python**: 3.11+
- **数据库**: SQLite 3.35+ (自带) 或 PostgreSQL 15+ (可选)
- **Redis**: 7.0+ (可选，缓存)
- **Docker**: 20.10+ (可选)

---

## 本地部署

### 1. 克隆项目

```bash
git clone https://github.com/minionszyw/cn5-lite.git
cd cn5-lite
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# AI模型（必需）
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# 数据库
DATABASE_PATH=data/cn5lite.db

# 数据源
DATA_SOURCE_PRIORITY=akshare,baostock,efinance

# 风控
TOTAL_CAPITAL=100000
MAX_TOTAL_LOSS_RATE=0.10
MAX_DAILY_LOSS_RATE=0.05

# 日志
LOG_LEVEL=INFO
LOG_FILE=logs/cn5lite.log
```

### 5. 初始化数据库

```bash
python -c "from app.database import init_db; init_db()"
```

### 6. 启动服务

**启动API服务**:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**启动UI界面**:
```bash
./start_ui.sh
# 或
streamlit run ui/app.py --server.port 8501
```

### 7. 访问

- **API文档**: http://localhost:8000/docs
- **UI界面**: http://localhost:8501

---

## Docker部署

### 1. 使用Docker Compose（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 2. 单独构建镜像

```bash
# 构建API镜像
docker build -t cn5lite-api -f Dockerfile.api .

# 构建UI镜像
docker build -t cn5lite-ui -f Dockerfile.ui .

# 运行容器
docker run -d -p 8000:8000 --env-file .env cn5lite-api
docker run -d -p 8501:8501 --env-file .env cn5lite-ui
```

### 3. Docker Compose配置示例

```yaml
version: '3.9'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  ui:
    build:
      context: .
      dockerfile: Dockerfile.ui
    ports:
      - "8501:8501"
    env_file:
      - .env
    depends_on:
      - api
    restart: unless-stopped

volumes:
  data:
  logs:
```

---

## 生产环境部署

### 1. 使用Supervisor管理进程

安装Supervisor:
```bash
sudo apt-get install supervisor
```

配置文件 `/etc/supervisor/conf.d/cn5lite.conf`:

```ini
[program:cn5lite-api]
command=/path/to/.venv/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000
directory=/path/to/cn5-lite
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/cn5lite/api.err.log
stdout_logfile=/var/log/cn5lite/api.out.log

[program:cn5lite-ui]
command=/path/to/.venv/bin/streamlit run ui/app.py --server.port 8501
directory=/path/to/cn5-lite
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/cn5lite/ui.err.log
stdout_logfile=/var/log/cn5lite/ui.out.log
```

启动服务:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start cn5lite-api
sudo supervisorctl start cn5lite-ui
```

### 2. 使用Nginx反向代理

配置文件 `/etc/nginx/sites-available/cn5lite`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # API代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # UI代理
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/cn5lite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. HTTPS配置（Let's Encrypt）

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 性能优化

### 1. 数据库优化

运行优化脚本:
```bash
python scripts/optimize_database.py
```

手动优化:
```sql
-- 启用WAL模式
PRAGMA journal_mode=WAL;

-- 设置缓存
PRAGMA cache_size=-64000;  -- 64MB

-- 创建索引
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_trades_date ON trades(trade_time);
```

### 2. API性能优化

在 `app/api/main.py` 添加缓存中间件:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="cn5lite-cache")
```

### 3. 并发配置

使用Gunicorn提高并发:

```bash
pip install gunicorn

# 启动4个worker
gunicorn app.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. 系统资源限制

设置ulimit:
```bash
ulimit -n 65536  # 文件描述符
ulimit -u 32768  # 进程数
```

---

## 监控和日志

### 1. 日志配置

日志文件位置:
- API日志: `logs/cn5lite_YYYY-MM-DD.log`
- 错误日志: `logs/error_YYYY-MM-DD.log`

配置日志级别（.env）:
```bash
LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR
LOG_RETENTION_DAYS=7
```

### 2. 监控指标

推荐使用Prometheus + Grafana:

安装Prometheus exporter:
```bash
pip install prometheus-fastapi-instrumentator
```

在 `app/api/main.py` 添加:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

访问指标: http://localhost:8000/metrics

### 3. 健康检查

API提供健康检查端点:
```bash
curl http://localhost:8000/health
```

设置定时检查:
```bash
# crontab -e
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart cn5lite-api
```

---

## 备份和恢复

### 1. 数据库备份

自动备份脚本:

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
DB_PATH="/path/to/data/cn5lite.db"

# 创建备份
sqlite3 $DB_PATH ".backup '$BACKUP_DIR/cn5lite_$DATE.db'"

# 压缩
gzip $BACKUP_DIR/cn5lite_$DATE.db

# 删除7天前的备份
find $BACKUP_DIR -name "*.db.gz" -mtime +7 -delete

echo "备份完成: cn5lite_$DATE.db.gz"
```

定时备份（crontab）:
```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh >> /var/log/cn5lite/backup.log 2>&1
```

### 2. 恢复数据库

```bash
# 解压备份
gunzip /path/to/backups/cn5lite_20240101.db.gz

# 停止服务
sudo supervisorctl stop cn5lite-api

# 恢复数据库
cp /path/to/backups/cn5lite_20240101.db /path/to/data/cn5lite.db

# 启动服务
sudo supervisorctl start cn5lite-api
```

### 3. 配置备份

备份重要配置文件:
```bash
tar -czf config_backup.tar.gz .env app/config.py
```

---

## 故障排除

### 问题1: API无法启动

**症状**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或更换端口
uvicorn app.api.main:app --port 8001
```

### 问题2: 数据库锁定

**症状**: `database is locked`

**解决**:
```bash
# 启用WAL模式
sqlite3 data/cn5lite.db "PRAGMA journal_mode=WAL;"

# 或重启服务
sudo supervisorctl restart cn5lite-api
```

### 问题3: 内存不足

**症状**: `MemoryError`

**解决**:
```bash
# 增加swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 限制进程内存
ulimit -v 2097152  # 2GB
```

### 问题4: AI API超时

**症状**: `Timeout waiting for AI response`

**解决**:
```python
# 增加超时时间（app/config.py）
AI_TIMEOUT = 180  # 秒
```

### 问题5: 数据源获取失败

**症状**: `All data sources failed`

**解决**:
```bash
# 检查网络
ping baidu.com

# 检查限流
# 查看日志确认是否触发限流

# 调整请求频率（app/config.py）
DATA_REQUEST_INTERVAL = 2  # 秒
```

---

## 安全建议

1. **API密钥保护**
   ```bash
   chmod 600 .env  # 限制权限
   ```

2. **防火墙配置**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **定期更新**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

4. **日志审计**
   - 定期检查 `logs/cn5lite_*.log`
   - 监控异常登录和API调用

---

## 扩展阅读

- [FastAPI部署文档](https://fastapi.tiangolo.com/deployment/)
- [Streamlit部署指南](https://docs.streamlit.io/deploy/streamlit-cloud)
- [SQLite性能优化](https://www.sqlite.org/optoverview.html)
- [Nginx配置](https://nginx.org/en/docs/)

---

**最后更新**: 2025-11-30
**版本**: 1.0.0
