import torch
import torch.nn as nn
import torchvision.models as models


def get_model(model_name='resnet50', num_classes=38, pretrained=True):
    """获取预训练模型并替换分类头。"""

    if model_name == 'resnet50':
        try:
            from torchvision.models import ResNet50_Weights
            weights = ResNet50_Weights.DEFAULT if pretrained else None
            model = models.resnet50(weights=weights)
        except ImportError:
            model = models.resnet50(pretrained=pretrained)
        model.fc = nn.Linear(model.fc.in_features, num_classes)

    elif model_name == 'efficientnet_b0':
        try:
            from torchvision.models import EfficientNet_B0_Weights
            weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
            model = models.efficientnet_b0(weights=weights)
        except ImportError:
            model = models.efficientnet_b0(pretrained=pretrained)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)

    else:
        raise ValueError(f"不支持模型 '{model_name}'，可选: resnet50, efficientnet_b0")

    return model


# ---------- 冻结 / 解冻 ----------

def freeze_backbone(model, model_name='resnet50'):
    """冻结 backbone，只保留分类头可训练。"""
    if model_name == 'resnet50':
        for name, param in model.named_parameters():
            if 'fc' not in name:
                param.requires_grad = False
    elif model_name == 'efficientnet_b0':
        for name, param in model.named_parameters():
            if 'classifier' not in name:
                param.requires_grad = False


def unfreeze_backbone(model):
    """解冻全部参数。"""
    for param in model.parameters():
        param.requires_grad = True


# ---------- 差分学习率参数组 ----------

def get_param_groups(model, model_name, backbone_lr, classifier_lr, weight_decay):
    """
    返回适用于 optimizer 的参数组列表：
      - backbone 用较小学习率
      - classifier 用较大学习率
    """
    if model_name == 'resnet50':
        backbone = [p for n, p in model.named_parameters() if 'fc' not in n and p.requires_grad]
        classifier = list(model.fc.parameters())
    elif model_name == 'efficientnet_b0':
        backbone = [p for n, p in model.named_parameters() if 'classifier' not in n and p.requires_grad]
        classifier = list(model.classifier.parameters())
    else:
        backbone = []
        classifier = list(model.parameters())

    return [
        {'params': backbone, 'lr': backbone_lr, 'weight_decay': weight_decay},
        {'params': classifier, 'lr': classifier_lr, 'weight_decay': weight_decay},
    ]
