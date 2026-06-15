# 🚀 部署指南

本文将指导你将代码实践平台部署到服务器，让任何人都能通过网址访问。

---

## 📋 前置要求

- 一台服务器（VPS、云主机均可），系统建议 **Ubuntu 20.04+** 或 **CentOS 7+**
- 服务器已安装 **Docker** 和 **Docker Compose**
- 一个域名（可选，不用域名可以直接用 IP 访问）
- DeepSeek API Key（[获取地址](https://platform.deepseek.com)）

---

## 🐳 方式一：Docker 部署（推荐）

### 1️⃣ 连接服务器

```bash
ssh root@你的服务器IP
```

### 2️⃣ 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3️⃣ 拉取代码

```bash
git clone https://github.com/liu-66-adc/my-project.git
cd my-project
```

### 4️⃣ 配置环境变量

```bash
cp .env.example .env
nano .env   # 编辑文件，填入 DEEPSEEK_API_KEY
```

### 5️⃣ 修改域名配置（可选）

编辑 `nginx.conf`，将 `server_name localhost;` 改为你的域名：

```nginx
server_name your-domain.com;
```

如果你有 **SSL 证书（HTTPS）**，取消注释 nginx.conf 中的 SSL 配置部分。

### 6️⃣ 启动服务

```bash
docker-compose up -d
```

### 7️⃣ 访问网站

打开浏览器访问：`http://你的服务器IP` 或 `https://你的域名`

---

## 🌐 方式二：云平台部署

### 部署到 Railway

[Railway](https://railway.app) 支持直接部署 Docker 项目：

1. Fork 此仓库到你的 GitHub
2. 在 Railway 中点击 **New Project → Deploy from GitHub repo**
3. 选择你的 fork
4. 添加环境变量 `DEEPSEEK_API_KEY`
5. Railway 自动构建部署

### 部署到 Render

[Render](https://render.com) 也支持 Docker 部署：

1. 在 Dashboard 点击 **New → Web Service**
2. 连接你的 GitHub 仓库
3. 选择 **Docker** 运行环境
4. 设置环境变量
5. 部署

---

## 🔧 常见生产配置

### 使用 HTTPS（推荐）

推荐使用 **Certbot** 自动申请免费 SSL 证书：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 申请证书（需要先配置域名DNS指向服务器）
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 配置防火墙

```bash
# 只开放必要端口
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
```

### 数据库持久化

默认使用 SQLite，数据存储在 `./data/` 目录。如需迁移到 MySQL/PostgreSQL：

```bash
# 在 .env 中修改
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

## 📊 监控服务

```bash
# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

---

## ❓ 常见问题

**Q: 部署后前端能访问但API报错？**
A: 检查 nginx.conf 中的 `proxy_pass http://backend:8000/api/;` — 确保容器网络连通。

**Q: 部署后出现 CORS 错误？**
A: 后端已配置 `ALLOWED_ORIGINS=*`，无需额外配置。

**Q: 如何更新代码？**
```bash
cd my-project
git pull
docker-compose down
docker-compose up -d --build
```

---

> 部署遇到问题？请提交 [GitHub Issue](https://github.com/liu-66-adc/my-project/issues)
