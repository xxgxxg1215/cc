# 农作物病害识别 - 后端 API 服务

基于 FastAPI + ONNX Runtime 的病害识别推理服务。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
uvicorn app:app --host 0.0.0.0 --port 8000
```

服务启动后访问 http://localhost:8000/docs 查看交互式 API 文档。

## 接口说明

### `GET /health`

健康检查，返回模型信息。

### `POST /predict`

上传图片进行病害识别。

**请求:** `multipart/form-data`，字段名 `file`

**响应示例:**
```json
{
  "prediction": "番茄 - 晚疫病",
  "disease_en": "Tomato___Late_blight",
  "confidence": 96.35,
  "is_healthy": false,
  "top5": [
    {"class_name": "Tomato___Late_blight", "name_cn": "番茄 - 晚疫病", "confidence": 96.35},
    ...
  ],
  "treatment": {
    "description": "病害描述...",
    "symptoms": "症状表现...",
    "cause": "发病原因...",
    "prevention": ["防治措施1", "..."],
    "medicine": ["推荐用药1", "..."]
  }
}
```

## 测试

```bash
curl -X POST -F "file=@test.jpg" http://localhost:8000/predict
```

## 目录结构

```
backend/
├── app.py              # FastAPI 主入口
├── disease_info.py     # 38种病害防治建议知识库
├── requirements.txt    # Python 依赖
├── model/
│   ├── resnet50.onnx   # ONNX 推理模型
│   └── class_labels.json
└── README.md
```
