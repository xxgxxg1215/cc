"""
模型导出脚本 —— 将训练好的 .pt 模型导出为 ONNX 格式 + 类别映射 JSON，
供后端推理服务（Flask / FastAPI + ONNX Runtime）或小程序云函数使用。

用法:
  python export_model.py --checkpoint logs/resnet50_ce_baseline_xxx/best_model.pt \
                         --model resnet50 --data_dir data/PlantVillage
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
import torch
from torchvision import datasets

from src.model import get_model


def export(args):
    # ---------- 类别列表 ----------
    ds = datasets.ImageFolder(root=args.data_dir)
    classes = ds.classes
    num_classes = len(classes)
    print(f"类别数: {num_classes}")

    # ---------- 加载模型 ----------
    model = get_model(args.model, num_classes=num_classes, pretrained=False)
    state = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(state)
    model.eval()
    print(f"已加载权重: {args.checkpoint}")

    out_dir = args.output_dir or os.path.dirname(args.checkpoint)
    os.makedirs(out_dir, exist_ok=True)

    # ---------- 导出 ONNX ----------
    onnx_path = os.path.join(out_dir, f"{args.model}.onnx")
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        model, dummy, onnx_path,
        input_names=['image'],
        output_names=['logits'],
        dynamic_axes={
            'image': {0: 'batch'},
            'logits': {0: 'batch'},
        },
        opset_version=12,
    )
    print(f"ONNX 模型已导出: {onnx_path}")

    # ---------- 类别映射 JSON ----------
    label_map = {i: name for i, name in enumerate(classes)}
    json_path = os.path.join(out_dir, "class_labels.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(label_map, f, indent=2, ensure_ascii=False)
    print(f"类别映射已保存: {json_path}")

    # ---------- 验证 ONNX ----------
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(onnx_path)
        out = sess.run(None, {'image': dummy.numpy()})
        pred = out[0].argmax(1)[0]
        print(f"ONNX Runtime 验证通过, 样例预测类别索引: {pred}")
    except ImportError:
        print("提示: 安装 onnxruntime 可验证导出结果 (pip install onnxruntime)")

    print(f"\n导出完成! 文件位于: {out_dir}")
    print("后端部署只需要两个文件:")
    print(f"  1. {onnx_path}")
    print(f"  2. {json_path}")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='导出模型为 ONNX')
    p.add_argument('--checkpoint', type=str, required=True,
                   help='训练好的 best_model.pt 路径')
    p.add_argument('--model', type=str, default='resnet50',
                   choices=['resnet50', 'efficientnet_b0'])
    p.add_argument('--data_dir', type=str, default='data/PlantVillage',
                   help='数据集目录（用于读取类别名）')
    p.add_argument('--output_dir', type=str, default=None,
                   help='导出目录，默认与 checkpoint 同目录')
    export(p.parse_args())
