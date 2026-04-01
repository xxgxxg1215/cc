import os
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, random_split, Dataset


class TransformedSubset(Dataset):
    """对 random_split 产生的 Subset 施加指定 transform。"""

    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform

    @property
    def classes(self):
        return self.subset.dataset.classes

    @property
    def class_to_idx(self):
        return self.subset.dataset.class_to_idx

    def __getitem__(self, index):
        x, y = self.subset[index]
        if self.transform:
            x = self.transform(x)
        return x, y

    def __len__(self):
        return len(self.subset)


def get_transforms(input_size=224):
    """返回 (train_transforms, test_transforms)。"""
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )

    train_transforms = transforms.Compose([
        transforms.Resize((input_size + 32, input_size + 32)),
        transforms.RandomCrop(input_size),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        normalize,
    ])

    test_transforms = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        normalize,
    ])

    return train_transforms, test_transforms


def get_datasets(data_dir, train_ratio=0.8, val_ratio=0.1, seed=42):
    """
    用 ImageFolder 加载数据，按比例划分 train / val / test，
    对 train 子集施加增强，val/test 只做 resize + normalize。
    """
    # 不传 transform，ImageFolder 返回 PIL Image
    full_dataset = datasets.ImageFolder(root=data_dir)

    total = len(full_dataset)
    train_size = int(train_ratio * total)
    val_size = int(val_ratio * total)
    test_size = total - train_size - val_size

    generator = torch.Generator().manual_seed(seed)
    train_sub, val_sub, test_sub = random_split(
        full_dataset, [train_size, val_size, test_size], generator=generator,
    )

    train_tf, test_tf = get_transforms()
    train_dataset = TransformedSubset(train_sub, train_tf)
    val_dataset = TransformedSubset(val_sub, test_tf)
    test_dataset = TransformedSubset(test_sub, test_tf)

    print(f"数据集: 训练 {train_size} | 验证 {val_size} | 测试 {test_size} | 类别 {len(full_dataset.classes)}")
    return train_dataset, val_dataset, test_dataset, full_dataset.classes


def get_dataloaders(data_dir, batch_size=32, num_workers=2):
    train_ds, val_ds, test_ds, classes = get_datasets(data_dir)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=True)

    return train_loader, val_loader, test_loader, classes
