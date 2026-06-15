# 🚀 代码实践平台 v2.0

> 模仿学习通AI实践的代码教学平台，支持AI自动评分 + JPlag代码查重
> 采用规范化项目结构，可直接部署运行。

## ✨ 功能特性

- ✅ **在线代码编辑** - 基于Monaco Editor（VS Code同款）
- ✅ **AI智能评分** - 调用DeepSeek API自动评分，给出详细改进建议
- ✅ **代码查重** - 集成JPlag，支持C++/C/Java/Python
- ✅ **教师看板** - 成绩统计、查重热力图、Excel导出
- ✅ **RESTful API** - 完整的API文档，支持扩展
- ✅ **Docker部署** - 一键容器化部署

## 🏗️ 项目结构

```
code-practice-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API路由层
│   │   ├── core/              # 核心业务（AI评分、查重）
│   │   ├── models/            # 数据模型 + 数据库操作
│   │   ├── services/          # 服务层
│   │   ├── utils/             # 工具函数
│   │   └── main.py            # FastAPI入口
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html             # 学生登录
│   ├── editor.html            # 代码编辑
│   └── teacher.html           # 教师看板
├── docker-compose.yml
├── nginx.conf
├── Makefile
├── start.sh / start.bat       # 一键启动脚本
└── README.md
```

## 🚀 快速开始

### 方式一：一键脚本启动（推荐）

**Mac/Linux:**
```bash
# 1. 克隆/解压项目
cd code-practice-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 3. 一键启动
./start.sh
```

**Windows:**
```cmd
# 1. 解压项目
cd code-practice-platform

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 3. 双击启动
start.bat
```

### 方式二：Docker部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env

# 2. 构建并启动
docker-compose up -d

# 3. 访问 http://localhost
```

### 方式三：手动启动

```bash
# 1. 安装Python依赖
cd backend
pip install -r requirements.txt

# 2. 下载JPlag（查重用）
cd ..
curl -L -o jplag-5.1.0.jar https://github.com/jplag/JPlag/releases/download/v5.1.0/jplag-5.1.0.jar

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env

# 4. 启动后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动前端（新终端）
cd frontend
python -m http.server 8080
```

## 🔑 配置说明

### 必须配置

| 配置项 | 说明 | 获取方式 |
|--------|------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | [platform.deepseek.com](https://platform.deepseek.com) |

### 可选配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | sqlite:///./data/database.sqlite | 数据库路径 |
| `JPLAG_JAR_PATH` | ./jplag-5.1.0.jar | JPlag路径 |
| `DEBUG` | false | 调试模式 |
| `LOG_LEVEL` | INFO | 日志级别 |

## 📖 使用指南

### 学生端

1. 访问 http://localhost:8080
2. 输入学号、姓名，选择课程
3. 选择任务，编写代码
4. 点击"提交评分"获取AI反馈
5. 根据建议修改，重新提交

### 教师端

1. 访问 http://localhost:8080/teacher.html
2. 选择任务，查看学生列表
3. 点击"运行查重"分析相似度
4. 查看热力图，发现异常
5. 导出Excel成绩表

## 🔌 API文档

启动后访问：http://localhost:8000/docs

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/student/login | 学生登录 |
| POST | /api/v1/student/submit | 提交代码 |
| GET | /api/v1/student/submission | 查询提交 |
| GET | /api/v1/teacher/submissions | 获取所有提交 |
| POST | /api/v1/teacher/plagiarism/check | 运行查重 |
| GET | /api/v1/teacher/export/grades | 导出成绩 |

## 🧪 开发指南

### 代码规范

```bash
# 格式化代码
make format

# 代码检查
make lint

# 运行测试
make test
```

### 项目规范

- **Python**: PEP 8 + 类型注解
- **API**: RESTful + 统一响应格式
- **Git**: 分支管理 + 规范提交信息
- **安全**: 输入验证 + 敏感信息环境变量

## 🐛 常见问题

**Q: pip install 很慢？**
A: 使用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

**Q: JPlag下载失败？**
A: 手动下载：[GitHub Releases](https://github.com/jplag/JPlag/releases)

**Q: AI评分没反应？**
A: 检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确

**Q: 前端打不开？**
A: 直接用浏览器打开 `frontend/index.html` 也可以

**Q: 如何部署到服务器？**
A: 使用Docker：`docker-compose up -d`

## 📄 许可证

MIT License - 学生项目自由使用

## 🤝 贡献

欢迎提交Issue和PR！

---

> 用 ❤️ 和 Python 构建
