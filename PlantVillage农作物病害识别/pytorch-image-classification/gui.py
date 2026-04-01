"""
农作物病害识别 - PyQt5 GUI
用法: python gui.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn.functional as F
from torchvision import transforms, datasets
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, QGroupBox, QProgressBar,
)
from PyQt5.QtGui import QPixmap, QFont, QImage
from PyQt5.QtCore import Qt

from src.model import get_model

# ================================================================
#  配置
# ================================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'PlantVillage')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

# 中文类名映射
CN_NAMES = {
    'Apple___Apple_scab': '苹果 - 黑星病',
    'Apple___Black_rot': '苹果 - 黑腐病',
    'Apple___Cedar_apple_rust': '苹果 - 雪松锈病',
    'Apple___healthy': '苹果 - 健康',
    'Blueberry___healthy': '蓝莓 - 健康',
    'Cherry_(including_sour)___healthy': '樱桃 - 健康',
    'Cherry_(including_sour)___Powdery_mildew': '樱桃 - 白粉病',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': '玉米 - 灰斑病',
    'Corn_(maize)___Common_rust_': '玉米 - 普通锈病',
    'Corn_(maize)___healthy': '玉米 - 健康',
    'Corn_(maize)___Northern_Leaf_Blight': '玉米 - 北方叶枯病',
    'Grape___Black_rot': '葡萄 - 黑腐病',
    'Grape___Esca_(Black_Measles)': '葡萄 - 黑麻疹',
    'Grape___healthy': '葡萄 - 健康',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': '葡萄 - 叶枯病',
    'Orange___Haunglongbing_(Citrus_greening)': '柑橘 - 黄龙病',
    'Peach___Bacterial_spot': '桃 - 细菌性斑点病',
    'Peach___healthy': '桃 - 健康',
    'Pepper,_bell___Bacterial_spot': '甜椒 - 细菌性斑点病',
    'Pepper,_bell___healthy': '甜椒 - 健康',
    'Potato___Early_blight': '马铃薯 - 早疫病',
    'Potato___healthy': '马铃薯 - 健康',
    'Potato___Late_blight': '马铃薯 - 晚疫病',
    'Raspberry___healthy': '树莓 - 健康',
    'Soybean___healthy': '大豆 - 健康',
    'Squash___Powdery_mildew': '南瓜 - 白粉病',
    'Strawberry___healthy': '草莓 - 健康',
    'Strawberry___Leaf_scorch': '草莓 - 叶焦病',
    'Tomato___Bacterial_spot': '番茄 - 细菌性斑点病',
    'Tomato___Early_blight': '番茄 - 早疫病',
    'Tomato___healthy': '番茄 - 健康',
    'Tomato___Late_blight': '番茄 - 晚疫病',
    'Tomato___Leaf_Mold': '番茄 - 叶霉病',
    'Tomato___Septoria_leaf_spot': '番茄 - 叶斑病',
    'Tomato___Spider_mites Two-spotted_spider_mite': '番茄 - 红蜘蛛',
    'Tomato___Target_Spot': '番茄 - 靶斑病',
    'Tomato___Tomato_mosaic_virus': '番茄 - 花叶病毒',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': '番茄 - 黄化曲叶病毒',
}

# ================================================================
#  推理预处理
# ================================================================

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


def find_checkpoints():
    """扫描 logs/ 下所有实验，返回 {显示名: checkpoint路径} 字典。"""
    results = {}
    if not os.path.isdir(LOG_DIR):
        return results
    for name in sorted(os.listdir(LOG_DIR)):
        ckpt = os.path.join(LOG_DIR, name, 'best_model.pt')
        if os.path.isfile(ckpt):
            results[name] = ckpt
    return results


def get_class_names():
    """从数据目录获取类名列表（按 ImageFolder 排序）。"""
    if os.path.isdir(DATA_DIR):
        ds = datasets.ImageFolder(root=DATA_DIR)
        return ds.classes
    return sorted(CN_NAMES.keys())


# ================================================================
#  主窗口
# ================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('农作物病害识别系统')
        self.setMinimumSize(800, 600)

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.classes = get_class_names()
        self.checkpoints = find_checkpoints()
        self.current_image_path = None

        self._build_ui()
        self._load_default_model()

    # ---------- UI ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # -- 模型选择区 --
        model_group = QGroupBox('模型选择')
        model_layout = QHBoxLayout(model_group)

        self.combo_ckpt = QComboBox()
        self.combo_ckpt.addItems(self.checkpoints.keys())
        model_layout.addWidget(QLabel('实验:'))
        model_layout.addWidget(self.combo_ckpt, 1)

        btn_load = QPushButton('加载模型')
        btn_load.clicked.connect(self._on_load_model)
        model_layout.addWidget(btn_load)

        self.label_model_status = QLabel('未加载')
        model_layout.addWidget(self.label_model_status)

        root_layout.addWidget(model_group)

        # -- 图片 + 结果 --
        content_layout = QHBoxLayout()

        # 左: 图片
        img_group = QGroupBox('输入图片')
        img_layout = QVBoxLayout(img_group)

        self.label_image = QLabel('请选择图片')
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setMinimumSize(400, 400)
        self.label_image.setStyleSheet('border: 2px dashed #aaa; background: #f9f9f9;')
        img_layout.addWidget(self.label_image)

        btn_layout = QHBoxLayout()
        btn_open = QPushButton('打开图片')
        btn_open.clicked.connect(self._on_open_image)
        btn_predict = QPushButton('开始识别')
        btn_predict.clicked.connect(self._on_predict)
        btn_predict.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_predict)
        img_layout.addLayout(btn_layout)

        content_layout.addWidget(img_group, 1)

        # 右: 结果
        result_group = QGroupBox('识别结果')
        result_layout = QVBoxLayout(result_group)

        self.label_result = QLabel('—')
        self.label_result.setFont(QFont('Microsoft YaHei', 18, QFont.Bold))
        self.label_result.setAlignment(Qt.AlignCenter)
        self.label_result.setWordWrap(True)
        result_layout.addWidget(self.label_result)

        self.label_conf = QLabel('')
        self.label_conf.setFont(QFont('Microsoft YaHei', 14))
        self.label_conf.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.label_conf)

        result_layout.addSpacing(10)
        self.label_top5_title = QLabel('Top-5 预测:')
        self.label_top5_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        result_layout.addWidget(self.label_top5_title)

        self.top5_bars = []
        self.top5_labels = []
        for _ in range(5):
            row = QHBoxLayout()
            lbl = QLabel('')
            lbl.setFont(QFont('Microsoft YaHei', 10))
            lbl.setMinimumWidth(180)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            row.addWidget(lbl, 0)
            row.addWidget(bar, 1)
            self.top5_labels.append(lbl)
            self.top5_bars.append(bar)
            result_layout.addLayout(row)

        result_layout.addStretch()
        content_layout.addWidget(result_group, 1)
        root_layout.addLayout(content_layout, 1)

        # -- 状态栏 --
        self.statusBar().showMessage(f'设备: {self.device}')

    # ---------- 逻辑 ----------

    def _model_name_from_exp(self, exp_name):
        if 'efficientnet' in exp_name:
            return 'efficientnet_b0'
        return 'resnet50'

    def _load_default_model(self):
        if not self.checkpoints:
            self.label_model_status.setText('logs/ 下无模型')
            return
        # 优先选 resnet50_ce_mixup
        for name in self.checkpoints:
            if 'mixup' in name and 'focal' not in name:
                self.combo_ckpt.setCurrentText(name)
                self._on_load_model()
                return
        # 否则加载第一个
        self.combo_ckpt.setCurrentIndex(0)
        self._on_load_model()

    def _on_load_model(self):
        exp_name = self.combo_ckpt.currentText()
        ckpt_path = self.checkpoints.get(exp_name)
        if not ckpt_path:
            return

        model_name = self._model_name_from_exp(exp_name)
        self.label_model_status.setText('加载中...')
        QApplication.processEvents()

        self.model = get_model(model_name, num_classes=len(self.classes), pretrained=False)
        state = torch.load(ckpt_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

        self.label_model_status.setText(f'{model_name} 已加载')
        self.statusBar().showMessage(f'设备: {self.device} | 模型: {exp_name}')

    def _on_open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择图片', '',
            '图片文件 (*.jpg *.jpeg *.png *.bmp *.webp);;所有文件 (*)')
        if not path:
            return

        self.current_image_path = path
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(
            self.label_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_image.setPixmap(scaled)

    def _on_predict(self):
        if self.model is None:
            self.label_result.setText('请先加载模型')
            return
        if self.current_image_path is None:
            self.label_result.setText('请先选择图片')
            return

        img = Image.open(self.current_image_path).convert('RGB')
        tensor = TRANSFORM(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1)[0]

        top5_prob, top5_idx = probs.topk(5)
        top5_prob = top5_prob.cpu().numpy()
        top5_idx = top5_idx.cpu().numpy()

        # Top-1
        cls_name = self.classes[top5_idx[0]]
        cn = CN_NAMES.get(cls_name, cls_name)
        conf = top5_prob[0] * 100

        self.label_result.setText(cn)
        self.label_conf.setText(f'置信度: {conf:.2f}%')

        if 'healthy' in cls_name:
            self.label_result.setStyleSheet('color: #4CAF50;')
        else:
            self.label_result.setStyleSheet('color: #F44336;')

        # Top-5
        for i in range(5):
            name = self.classes[top5_idx[i]]
            cn_name = CN_NAMES.get(name, name)
            pct = top5_prob[i] * 100
            self.top5_labels[i].setText(cn_name)
            self.top5_bars[i].setValue(int(pct))
            self.top5_bars[i].setFormat(f'{pct:.2f}%')


# ================================================================
#  入口
# ================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
