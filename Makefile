.PHONY: install start stop test lint clean docker-build docker-up

# 安装依赖
install:
	cd backend && pip install -r requirements.txt

# 本地启动
start:
	./start.sh

# 停止服务
stop:
	pkill -f "uvicorn" || true
	pkill -f "http.server" || true

# 运行测试
test:
	cd backend && pytest tests/ -v

# 代码检查
lint:
	cd backend && black app/ --check
	cd backend && flake8 app/

# 格式化代码
format:
	cd backend && black app/

# 清理
clean:
	rm -rf data/* submissions/* jplag-results/* exports/*
	find . -type d -name __pycache__ -exec rm -rf {} +

# Docker构建
docker-build:
	docker-compose build

# Docker启动
docker-up:
	docker-compose up -d

# Docker停止
docker-down:
	docker-compose down
