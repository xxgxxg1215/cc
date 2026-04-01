"""
PlantVillage 对比实验训练脚本

用法示例:
  # 基线 ResNet50
  python src/train.py --model resnet50 --loss ce --epochs 30

  # 基线 EfficientNet-B0
  python src/train.py --model efficientnet_b0 --loss ce --epochs 30

  # ResNet50 + Focal Loss
  python src/train.py --model resnet50 --loss focal --epochs 30

  # ResNet50 + Mixup
  python src/train.py --model resnet50 --loss ce --mixup --epochs 30

  # ResNet50 + CutMix
  python src/train.py --model resnet50 --loss ce --cutmix --epochs 30

  # ResNet50 + Focal + Mixup（最终优化组合）
  python src/train.py --model resnet50 --loss focal --mixup --epochs 30

  # 对比所有实验结果
  python src/train.py --compare
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.optim as optim
import argparse
import time
import numpy as np

from src.dataset import get_dataloaders
from src.model import get_model, freeze_backbone, unfreeze_backbone, get_param_groups
from src.utils import (
    count_parameters, calculate_accuracy, epoch_time,
    TrainingHistory, plot_training_curves, plot_confusion,
    evaluate_per_class, compare_experiments,
    FocalLoss, mixup_data, cutmix_data, mixup_criterion,
)


# ================================================================
#  训练 / 评估一个 epoch
# ================================================================

def train_one_epoch(model, loader, optimizer, criterion, device,
                    use_mixup=False, use_cutmix=False, mix_alpha=0.2):
    model.train()
    total_loss, total_acc, n = 0.0, 0.0, 0

    for x, y in loader:
        x, y = x.to(device), y.to(device)

        # ---------- 数据混合增强 ----------
        if use_mixup and use_cutmix:
            # 两者都开启时每个 batch 随机二选一
            if np.random.rand() > 0.5:
                x, y_a, y_b, lam = mixup_data(x, y, alpha=mix_alpha)
            else:
                x, y_a, y_b, lam = cutmix_data(x, y, alpha=mix_alpha)
            mixed = True
        elif use_mixup:
            x, y_a, y_b, lam = mixup_data(x, y, alpha=mix_alpha)
            mixed = True
        elif use_cutmix:
            x, y_a, y_b, lam = cutmix_data(x, y, alpha=mix_alpha)
            mixed = True
        else:
            mixed = False

        optimizer.zero_grad()
        pred = model(x)

        if mixed:
            loss = mixup_criterion(criterion, pred, y_a, y_b, lam)
            acc = lam * calculate_accuracy(pred, y_a) + (1 - lam) * calculate_accuracy(pred, y_b)
        else:
            loss = criterion(pred, y)
            acc = calculate_accuracy(pred, y)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        total_acc += acc.item()
        n += 1

    return total_loss / n, total_acc / n


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, total_acc, n = 0.0, 0.0, 0

    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x)
        loss = criterion(pred, y)
        acc = calculate_accuracy(pred, y)
        total_loss += loss.item()
        total_acc += acc.item()
        n += 1

    return total_loss / n, total_acc / n


# ================================================================
#  主函数
# ================================================================

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_data = os.path.join(project_root, 'data', 'PlantVillage')
    default_log = os.path.join(project_root, 'logs')

    p = argparse.ArgumentParser(description='PlantVillage 对比实验训练')

    # 数据
    p.add_argument('--data_dir', type=str, default=default_data)
    p.add_argument('--batch_size', type=int, default=32)
    p.add_argument('--num_workers', type=int, default=2)

    # 模型
    p.add_argument('--model', type=str, default='resnet50',
                   choices=['resnet50', 'efficientnet_b0'])
    p.add_argument('--freeze_epochs', type=int, default=5,
                   help='冻结 backbone 的 epoch 数，0=不冻结')

    # 训练
    p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--weight_decay', type=float, default=1e-4)
    p.add_argument('--patience', type=int, default=7,
                   help='Early stopping patience，0=不启用')

    # 损失函数
    p.add_argument('--loss', type=str, default='ce', choices=['ce', 'focal'])
    p.add_argument('--focal_gamma', type=float, default=2.0)
    p.add_argument('--focal_alpha', type=float, default=0.25)

    # 数据混合增强
    p.add_argument('--mixup', action='store_true', help='启用 Mixup')
    p.add_argument('--cutmix', action='store_true', help='启用 CutMix')
    p.add_argument('--mix_alpha', type=float, default=0.2,
                   help='Mixup/CutMix 的 Beta 分布参数')

    # 学习率调度
    p.add_argument('--scheduler', type=str, default='cosine',
                   choices=['cosine', 'plateau', 'none'])

    # 其他
    p.add_argument('--device', type=str,
                   default='cuda' if torch.cuda.is_available() else 'cpu')
    p.add_argument('--log_dir', type=str, default=default_log)
    p.add_argument('--save_name', type=str, default='best_model.pt')

    # 对比模式
    p.add_argument('--compare', action='store_true',
                   help='不训练，只对比 logs 下已有实验')

    args = p.parse_args()

    # ---------- 对比模式 ----------
    if args.compare:
        compare_experiments(args.log_dir)
        return

    # ---------- 构建实验配置描述 ----------
    aug_parts = []
    if args.mixup:
        aug_parts.append('mixup')
    if args.cutmix:
        aug_parts.append('cutmix')
    augment_desc = '+'.join(aug_parts) if aug_parts else 'baseline'

    config = {
        'model': args.model,
        'loss': args.loss,
        'augment': augment_desc,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'scheduler': args.scheduler,
        'freeze_epochs': args.freeze_epochs,
        'batch_size': args.batch_size,
        'epochs': args.epochs,
        'patience': args.patience,
        'focal_gamma': args.focal_gamma if args.loss == 'focal' else None,
        'focal_alpha': args.focal_alpha if args.loss == 'focal' else None,
        'mix_alpha': args.mix_alpha if aug_parts else None,
    }

    print('=' * 60)
    print(f'模型: {args.model}  |  损失: {args.loss}  |  增强: {augment_desc}')
    print(f'设备: {args.device}  |  数据: {args.data_dir}')
    print('=' * 60)

    # ---------- 数据 ----------
    train_loader, val_loader, test_loader, classes = get_dataloaders(
        args.data_dir, args.batch_size, args.num_workers)
    num_classes = len(classes)

    # ---------- 模型 ----------
    model = get_model(args.model, num_classes=num_classes).to(args.device)

    if args.freeze_epochs > 0:
        freeze_backbone(model, args.model)
        print(f'已冻结 backbone，前 {args.freeze_epochs} epochs 只训练分类头')

    trainable = count_parameters(model)
    print(f'类别: {num_classes}  |  可训练参数: {trainable:,}')

    # ---------- 损失函数 ----------
    if args.loss == 'focal':
        criterion = FocalLoss(gamma=args.focal_gamma, alpha=args.focal_alpha)
        print(f'损失函数: Focal Loss (gamma={args.focal_gamma}, alpha={args.focal_alpha})')
    else:
        criterion = nn.CrossEntropyLoss()
        print('损失函数: CrossEntropyLoss')
    criterion = criterion.to(args.device)

    # ---------- 优化器 ----------
    optimizer = optim.Adam(
        filter(lambda pa: pa.requires_grad, model.parameters()),
        lr=args.lr, weight_decay=args.weight_decay,
    )

    # ---------- 学习率调度器 ----------
    if args.scheduler == 'cosine':
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    elif args.scheduler == 'plateau':
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='max', patience=3, factor=0.5)
    else:
        scheduler = None
    print(f'调度器: {args.scheduler}')

    # ---------- 训练历史 ----------
    exp_label = f"{args.model}_{args.loss}_{augment_desc}"
    history = TrainingHistory(save_dir=args.log_dir, model_name=exp_label, config=config)
    print(f'日志目录: {history.save_dir}\n')

    # ---------- 训练循环 ----------
    best_val_acc = 0.0
    patience_counter = 0

    for epoch in range(1, args.epochs + 1):
        # --- 解冻 backbone ---
        if args.freeze_epochs > 0 and epoch == args.freeze_epochs + 1:
            unfreeze_backbone(model)
            optimizer = optim.Adam(
                get_param_groups(model, args.model,
                                 backbone_lr=args.lr * 0.1,
                                 classifier_lr=args.lr,
                                 weight_decay=args.weight_decay),
            )
            if args.scheduler == 'cosine':
                scheduler = optim.lr_scheduler.CosineAnnealingLR(
                    optimizer, T_max=args.epochs - args.freeze_epochs)
            elif args.scheduler == 'plateau':
                scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                    optimizer, mode='max', patience=3, factor=0.5)
            trainable = count_parameters(model)
            print(f'\n>>> Epoch {epoch}: 解冻 backbone，差分学习率微调 '
                  f'(backbone lr={args.lr * 0.1:.1e}, head lr={args.lr:.1e}), '
                  f'可训练参数: {trainable:,}')

        t0 = time.time()

        train_loss, train_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, args.device,
            use_mixup=args.mixup, use_cutmix=args.cutmix, mix_alpha=args.mix_alpha,
        )
        val_loss, val_acc = evaluate(model, val_loader, criterion, args.device)

        t1 = time.time()
        mins, secs = epoch_time(t0, t1)

        # 调度器 step
        if scheduler:
            if args.scheduler == 'plateau':
                scheduler.step(val_acc)
            else:
                scheduler.step()

        lr_now = optimizer.param_groups[0]['lr']
        history.log_epoch(epoch, train_loss, train_acc, val_loss, val_acc, lr_now, t1 - t0)

        # 保存最佳模型（按验证准确率）
        marker = ''
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(),
                       os.path.join(history.save_dir, args.save_name))
            patience_counter = 0
            marker = '  ★ saved'
        else:
            patience_counter += 1

        print(f'Epoch {epoch:02}/{args.epochs} [{mins}m{secs}s]  '
              f'Train {train_loss:.4f}/{train_acc * 100:.2f}%  '
              f'Val {val_loss:.4f}/{val_acc * 100:.2f}%  '
              f'LR {lr_now:.2e}{marker}')

        # Early stopping
        if args.patience > 0 and patience_counter >= args.patience:
            print(f'\nEarly stopping: 验证准确率连续 {args.patience} epochs 未提升')
            break

    # ---------- 保存训练历史 & 曲线 ----------
    history.save()
    plot_training_curves(history.history, history.save_dir)

    # ---------- 测试集评估 ----------
    best_path = os.path.join(history.save_dir, args.save_name)
    model.load_state_dict(torch.load(best_path, map_location=args.device, weights_only=True))

    test_loss, test_acc = evaluate(model, test_loader, criterion, args.device)
    report, labels, preds = evaluate_per_class(model, test_loader, classes, args.device)

    # 保存分类报告
    report_path = os.path.join(history.save_dir, 'classification_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"模型: {args.model} | 损失: {args.loss} | 增强: {augment_desc}\n")
        f.write(f"测试集 Loss: {test_loss:.4f} | 测试集 Acc: {test_acc * 100:.2f}%\n")
        f.write(f"最佳验证 Acc: {best_val_acc * 100:.2f}% (Epoch {history.best_epoch})\n\n")
        f.write(report)
    print(f'\n分类报告已保存: {report_path}')

    # 混淆矩阵
    plot_confusion(labels, preds, classes, history.save_dir)

    print(f'\n{"=" * 60}')
    print(f'测试集 Acc: {test_acc * 100:.2f}%  |  最佳验证 Acc: {best_val_acc * 100:.2f}%')
    print(f'所有结果: {history.save_dir}')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
