import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import json
import os
import glob
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay


# ================================================================
#  基础工具
# ================================================================

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def calculate_accuracy(y_pred, y):
    top_pred = y_pred.argmax(1, keepdim=True)
    correct = top_pred.eq(y.view_as(top_pred)).sum()
    return correct.float() / y.shape[0]


def epoch_time(start_time, end_time):
    elapsed = end_time - start_time
    mins = int(elapsed / 60)
    secs = int(elapsed - mins * 60)
    return mins, secs


# ================================================================
#  Focal Loss
# ================================================================

class FocalLoss(nn.Module):
    """
    Focal Loss: 下调容易样本的权重，聚焦难样本。
      FL(p_t) = -alpha * (1 - p_t)^gamma * log(p_t)
    """

    def __init__(self, gamma=2.0, alpha=None, reduction='mean'):
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce)
        focal = ((1 - pt) ** self.gamma) * ce
        if self.alpha is not None:
            focal = self.alpha * focal
        if self.reduction == 'mean':
            return focal.mean()
        elif self.reduction == 'sum':
            return focal.sum()
        return focal


# ================================================================
#  Mixup / CutMix
# ================================================================

def mixup_data(x, y, alpha=0.2):
    """对一个 batch 做 Mixup，返回 (mixed_x, y_a, y_b, lam)。"""
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    mixed = lam * x + (1 - lam) * x[idx]
    return mixed, y, y[idx], lam


def cutmix_data(x, y, alpha=1.0):
    """对一个 batch 做 CutMix，返回 (mixed_x, y_a, y_b, lam)。"""
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    B, C, H, W = x.shape

    cut_ratio = np.sqrt(1.0 - lam)
    rw, rh = int(W * cut_ratio), int(H * cut_ratio)
    cx, cy = np.random.randint(W), np.random.randint(H)
    x1, x2 = np.clip(cx - rw // 2, 0, W), np.clip(cx + rw // 2, 0, W)
    y1, y2 = np.clip(cy - rh // 2, 0, H), np.clip(cy + rh // 2, 0, H)

    mixed = x.clone()
    mixed[:, :, y1:y2, x1:x2] = x[idx, :, y1:y2, x1:x2]
    lam = 1 - (x2 - x1) * (y2 - y1) / (W * H)  # 按实际面积修正
    return mixed, y, y[idx], lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Mixup / CutMix 对应的混合损失。"""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ================================================================
#  逐类评估
# ================================================================

def evaluate_per_class(model, data_loader, classes, device):
    """在给定 loader 上做推理，返回 sklearn classification_report 字符串。"""
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for x, y in data_loader:
            x = x.to(device)
            preds = model(x).argmax(1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(y.numpy())
    report = classification_report(all_labels, all_preds,
                                   target_names=classes, digits=4)
    return report, all_labels, all_preds


# ================================================================
#  训练历史记录
# ================================================================

class TrainingHistory:
    """记录训练过程并保存为 JSON。"""

    def __init__(self, save_dir, model_name='model', config=None):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.experiment_name = f"{model_name}_{timestamp}"
        self.save_dir = os.path.join(save_dir, self.experiment_name)
        os.makedirs(self.save_dir, exist_ok=True)

        self.config = config or {}
        self.history = {
            'train_loss': [], 'train_acc': [],
            'val_loss': [], 'val_acc': [],
            'lr': [], 'epoch_time': [],
        }
        self.best_val_acc = 0.0
        self.best_epoch = 0

    def log_epoch(self, epoch, train_loss, train_acc, val_loss, val_acc, lr, epoch_time_sec):
        self.history['train_loss'].append(train_loss)
        self.history['train_acc'].append(train_acc)
        self.history['val_loss'].append(val_loss)
        self.history['val_acc'].append(val_acc)
        self.history['lr'].append(lr)
        self.history['epoch_time'].append(epoch_time_sec)
        if val_acc > self.best_val_acc:
            self.best_val_acc = val_acc
            self.best_epoch = epoch

    def save(self):
        record = {
            'config': self.config,
            'history': self.history,
            'best_val_acc': self.best_val_acc,
            'best_epoch': self.best_epoch,
            'total_epochs': len(self.history['train_loss']),
        }
        path = os.path.join(self.save_dir, 'history.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        print(f"训练历史已保存: {path}")
        return path


# ================================================================
#  绘图
# ================================================================

def plot_training_curves(history, save_dir):
    """绘制损失 / 准确率 / 学习率 / 过拟合差距四合一图。"""
    epochs = range(1, len(history['train_loss']) + 1)
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 损失
    ax = axes[0, 0]
    ax.plot(epochs, history['train_loss'], 'b-o', ms=3, label='训练损失')
    ax.plot(epochs, history['val_loss'], 'r-o', ms=3, label='验证损失')
    ax.set_xlabel('Epoch'); ax.set_ylabel('Loss'); ax.set_title('损失曲线')
    ax.legend(); ax.grid(True, alpha=0.3)

    # 准确率
    ax = axes[0, 1]
    tr_acc = [a * 100 for a in history['train_acc']]
    va_acc = [a * 100 for a in history['val_acc']]
    ax.plot(epochs, tr_acc, 'b-o', ms=3, label='训练准确率')
    ax.plot(epochs, va_acc, 'r-o', ms=3, label='验证准确率')
    ax.set_xlabel('Epoch'); ax.set_ylabel('Accuracy (%)'); ax.set_title('准确率曲线')
    ax.legend(); ax.grid(True, alpha=0.3)

    # 学习率
    ax = axes[1, 0]
    ax.plot(epochs, history['lr'], 'g-o', ms=3, label='学习率')
    ax.set_xlabel('Epoch'); ax.set_ylabel('LR'); ax.set_title('学习率变化')
    ax.legend(); ax.grid(True, alpha=0.3)
    ax.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))

    # 过拟合差距
    ax = axes[1, 1]
    gap = [t - v for t, v in zip(tr_acc, va_acc)]
    ax.plot(epochs, gap, 'm-o', ms=3, label='训练-验证准确率差')
    ax.axhline(y=0, color='k', ls='--', alpha=0.3)
    ax.set_xlabel('Epoch'); ax.set_ylabel('Gap (%)'); ax.set_title('过拟合监控')
    ax.legend(); ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(save_dir, 'training_curves.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"训练曲线已保存: {path}")
    return path


def plot_confusion(labels, preds, classes, save_dir):
    """绘制混淆矩阵并保存。"""
    cm = confusion_matrix(labels, preds)
    fig, ax = plt.subplots(figsize=(16, 14))
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    disp = ConfusionMatrixDisplay(cm, display_labels=classes)
    disp.plot(values_format='d', cmap='Blues', ax=ax, xticks_rotation=45)
    plt.tight_layout()
    path = os.path.join(save_dir, 'confusion_matrix.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"混淆矩阵已保存: {path}")
    return path


# ================================================================
#  多实验对比
# ================================================================

def compare_experiments(log_dir):
    """
    读取 log_dir 下所有实验的 history.json，
    按 best_val_acc 降序打印对比表格，并返回结果列表。
    """
    rows = []
    for hpath in sorted(glob.glob(os.path.join(log_dir, '*/history.json'))):
        with open(hpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cfg = data.get('config', {})
        rows.append({
            'name': os.path.basename(os.path.dirname(hpath)),
            'model': cfg.get('model', '?'),
            'loss': cfg.get('loss', '?'),
            'augment': cfg.get('augment', '-'),
            'best_val_acc': data['best_val_acc'] * 100,
            'best_epoch': data['best_epoch'],
            'epochs': data['total_epochs'],
        })

    rows.sort(key=lambda r: r['best_val_acc'], reverse=True)

    header = f"{'实验':<40} {'模型':<16} {'Loss':<8} {'增强':<12} {'BestValAcc':>10} {'Epoch':>6}"
    sep = '=' * len(header)
    print(f"\n{sep}\n{header}\n{sep}")
    for r in rows:
        print(f"{r['name']:<40} {r['model']:<16} {r['loss']:<8} {r['augment']:<12} "
              f"{r['best_val_acc']:>9.2f}% {r['best_epoch']:>6}")
    print(sep)
    return rows
