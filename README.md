# Blogin Sentiment Blog

这是一个基于 Flask API 和 Vue/Vite 的个人博客系统，评论提交时会自动进行情感分析。

## 目录结构

```text
.
├── server/              # Flask API 后端
├── frontend/            # Vue + Vite 前端
├── model/               # 情感分析模型推理服务
├── data/                # MySQL 数据卷与运行日志目录
└── docker-compose.yml   # MySQL、Redis、Flask、模型服务、Vite 编排
```

## 启动

```bash
docker-compose up --build -d
```

前端地址：

```text
http://127.0.0.1:5173
```

后端健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 初始化

```bash
docker exec -e FLASK_APP=server.wsgi:app blogin flask initdb
docker exec -e FLASK_APP=server.wsgi:app blogin flask admin
```

站点信息、管理员账号和情感分析服务地址均在 `.env` 中配置。
