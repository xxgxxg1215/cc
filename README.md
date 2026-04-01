# 🌾 农作物病害识别系统

基于深度学习的农作物病害识别平台，由微信小程序 + FastAPI 后端构成，支持拍照上传、AI 智能识别（ResNet-50 / ONNX）、病害百科、识别历史、社区交流、天气查询等功能，并提供 Web 管理后台。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 微信小程序（原生 WXML / WXSS / JS） |
| 后端 | Python 3.10+ · FastAPI · Uvicorn |
| AI 推理 | ONNX Runtime · ResNet-50（38 类病害） |
| 数据库 | MySQL 8.0+ · SQLAlchemy ORM |
| 认证 | 微信 OAuth + JWT |
| 天气 | Open-Meteo（免费无需 Key）+ OSM Nominatim 地名反查 |

---

## 目录结构

```
农作物识别/
├── backend/                  # FastAPI 后端
│   ├── app.py                # 主入口
│   ├── config.py             # 环境配置
│   ├── database.py           # 数据库连接
│   ├── models.py             # SQLAlchemy 数据模型
│   ├── disease_info.py       # 38 种病害知识库
│   ├── init_db.py            # 数据库初始化脚本
│   ├── requirements.txt      # Python 依赖
│   ├── model/
│   │   ├── resnet50.onnx     # ONNX 推理模型
│   │   └── class_labels.json # 类别标签
│   ├── routers/              # 各功能路由模块
│   │   ├── predict.py        # 病害识别
│   │   ├── user.py           # 用户（微信登录）
│   │   ├── history.py        # 识别历史
│   │   ├── encyclopedia.py   # 病害百科
│   │   ├── community.py      # 社区帖子
│   │   ├── weather.py        # 天气查询
│   │   ├── news.py           # 新闻资讯
│   │   └── admin.py          # 管理后台
│   ├── templates/            # 管理后台 HTML 模板
│   └── uploads/              # 上传图片存储目录
└── mini-program/             # 微信小程序源码
    ├── app.js / app.json
    ├── pages/                # 各页面
    ├── static/               # 静态资源
    └── utils/                # 工具函数
```

---

## 环境准备

### 后端依赖

- Python **3.10+**
- MySQL **8.0+**（需提前创建数据库）
- （可选）微信公众平台账号、和风天气 Key

### 前端依赖

- [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)

---

## 🚀 本地启动

### 1. 创建 MySQL 数据库

```sql
CREATE DATABASE crop_disease CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

默认配置已可直接使用（MySQL root/123456）。如需自定义，在 `backend/` 目录创建 `.env` 文件或直接设置以下环境变量：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DB=crop_disease

# 微信小程序（上线必填）
WX_APPID=你的AppID
WX_SECRET=你的AppSecret

# 管理后台账号（默认 admin / admin123）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# JWT 密钥（生产环境务必修改）
SECRET_KEY=your-secret-key
```

### 4. 启动后端服务

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> 首次启动会自动建表，无需手动执行迁移。
>
> 如果 8000 端口被占用，可换端口：`--port 8001`

启动成功后访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8000/docs | Swagger 交互式 API 文档 |
| http://localhost:8000/redoc | ReDoc API 文档 |
| http://localhost:8000/admin | Web 管理后台（需登录） |

### 5. 启动微信小程序

1. 打开**微信开发者工具**
2. 导入项目，选择 `mini-program/` 目录
3. 在 `mini-program/utils/` 中找到请求基地址配置，将其改为：
   ```
   http://localhost:8000
   ```
4. 点击「编译」即可预览

---

## API 速查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/predict` | 上传图片识别病害 |
| POST | `/user/login` | 微信登录 |
| GET | `/history` | 获取识别历史 |
| GET | `/encyclopedia` | 病害百科列表 |
| GET | `/community/posts` | 社区帖子列表 |
| GET | `/weather` | 天气查询 |
| GET | `/news` | 新闻资讯 |
| GET | `/admin` | 管理后台（Web） |

完整接口详见启动后的 `/docs` 页面。

---

## 管理后台

浏览器访问 `http://localhost:8000/admin`，默认账号：

- 用户名：`admin`
- 密码：`admin123`

支持用户管理、百科内容管理、新闻发布等功能。

---

## 识别能力

模型支持 **38 类**农作物病害识别，涵盖：

苹果、蓝莓、樱桃、玉米、葡萄、柑橘、桃子、辣椒、马铃薯、草莓、番茄等植物的常见病害，以及健康状态判断。

---

## 常见问题

**Q: 端口 8000 被占用？**
```bash
uvicorn app:app --port 8001
```
同时修改小程序中的请求基地址。

**Q: 数据库连接失败？**
检查 MySQL 是否已启动，以及 `config.py` / 环境变量中的账号密码是否正确。

**Q: 小程序无法连接后端？**
微信开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名」。
