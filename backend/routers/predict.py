"""
/predict — 病害识别接口（从 app.py 拆出）
"""
import os, json, uuid, shutil
import numpy as np
from io import BytesIO

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends
from PIL import Image
from sqlalchemy.orm import Session

import onnxruntime as ort

from database import get_db
from models import RecognitionHistory
from disease_info import get_disease_info
from config import UPLOAD_DIR

router = APIRouter(prefix="", tags=["识别"])

# ── 模型加载 ──
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")
# 兼容：如果 model 目录和 routers 同级
if not os.path.isdir(MODEL_DIR):
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model")
ONNX_PATH = os.path.join(MODEL_DIR, "resnet50.onnx")
LABELS_PATH = os.path.join(MODEL_DIR, "class_labels.json")

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

CN_NAMES = {
    "Apple___Apple_scab": "苹果 - 黑星病",
    "Apple___Black_rot": "苹果 - 黑腐病",
    "Apple___Cedar_apple_rust": "苹果 - 雪松锈病",
    "Apple___healthy": "苹果 - 健康",
    "Blueberry___healthy": "蓝莓 - 健康",
    "Cherry_(including_sour)___healthy": "樱桃 - 健康",
    "Cherry_(including_sour)___Powdery_mildew": "樱桃 - 白粉病",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "玉米 - 灰斑病",
    "Corn_(maize)___Common_rust_": "玉米 - 普通锈病",
    "Corn_(maize)___healthy": "玉米 - 健康",
    "Corn_(maize)___Northern_Leaf_Blight": "玉米 - 北方叶枯病",
    "Grape___Black_rot": "葡萄 - 黑腐病",
    "Grape___Esca_(Black_Measles)": "葡萄 - 黑麻疹",
    "Grape___healthy": "葡萄 - 健康",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "葡萄 - 叶枯病",
    "Orange___Haunglongbing_(Citrus_greening)": "柑橘 - 黄龙病",
    "Peach___Bacterial_spot": "桃 - 细菌性斑点病",
    "Peach___healthy": "桃 - 健康",
    "Pepper,_bell___Bacterial_spot": "甜椒 - 细菌性斑点病",
    "Pepper,_bell___healthy": "甜椒 - 健康",
    "Potato___Early_blight": "马铃薯 - 早疫病",
    "Potato___healthy": "马铃薯 - 健康",
    "Potato___Late_blight": "马铃薯 - 晚疫病",
    "Raspberry___healthy": "树莓 - 健康",
    "Soybean___healthy": "大豆 - 健康",
    "Squash___Powdery_mildew": "南瓜 - 白粉病",
    "Strawberry___healthy": "草莓 - 健康",
    "Strawberry___Leaf_scorch": "草莓 - 叶焦病",
    "Tomato___Bacterial_spot": "番茄 - 细菌性斑点病",
    "Tomato___Early_blight": "番茄 - 早疫病",
    "Tomato___healthy": "番茄 - 健康",
    "Tomato___Late_blight": "番茄 - 晚疫病",
    "Tomato___Leaf_Mold": "番茄 - 叶霉病",
    "Tomato___Septoria_leaf_spot": "番茄 - 叶斑病",
    "Tomato___Spider_mites Two-spotted_spider_mite": "番茄 - 红蜘蛛",
    "Tomato___Target_Spot": "番茄 - 靶斑病",
    "Tomato___Tomato_mosaic_virus": "番茄 - 花叶病毒",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "番茄 - 黄化曲叶病毒",
}

with open(LABELS_PATH, "r", encoding="utf-8") as f:
    LABEL_MAP = json.load(f)
CLASS_NAMES = [LABEL_MAP[str(i)] for i in range(len(LABEL_MAP))]

session_onnx = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
INPUT_NAME = session_onnx.get_inputs()[0].name


def preprocess(image: Image.Image) -> np.ndarray:
    img = image.convert("RGB").resize((224, 224), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - MEAN) / STD
    arr = arr.transpose(2, 0, 1)
    return arr[np.newaxis, ...]


def softmax(logits: np.ndarray) -> np.ndarray:
    e = np.exp(logits - logits.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "resnet50_focal_mixup",
        "num_classes": len(CLASS_NAMES),
    }


@router.post("/predict")
async def predict(
    file: UploadFile = File(...),
    user_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        image = Image.open(BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析上传的图片文件")

    # 保存图片到 uploads/
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    with open(save_path, "wb") as f:
        f.write(content)

    # 推理
    tensor = preprocess(image)
    logits = session_onnx.run(None, {INPUT_NAME: tensor})[0]
    probs = softmax(logits)[0]

    top5_idx = probs.argsort()[::-1][:5]
    top5 = []
    for idx in top5_idx:
        cls_en = CLASS_NAMES[idx]
        top5.append({
            "class_name": cls_en,
            "name_cn": CN_NAMES.get(cls_en, cls_en),
            "confidence": round(float(probs[idx]) * 100, 2),
        })

    best = top5[0]
    disease_en = best["class_name"]
    is_healthy = "healthy" in disease_en
    info = get_disease_info(disease_en)

    # 写库（可选）
    if user_id:
        record = RecognitionHistory(
            user_id=user_id,
            image_url=f"/uploads/{filename}",
            prediction=best["name_cn"],
            disease_en=disease_en,
            confidence=best["confidence"],
            is_healthy=is_healthy,
        )
        db.add(record)
        db.commit()

    return {
        "prediction": best["name_cn"],
        "disease_en": disease_en,
        "confidence": best["confidence"],
        "is_healthy": is_healthy,
        "image_url": f"/uploads/{filename}",
        "top5": top5,
        "treatment": {
            "description": info["description"],
            "symptoms": info["symptoms"],
            "cause": info["cause"],
            "prevention": info["prevention"],
            "medicine": info["medicine"],
        },
    }
