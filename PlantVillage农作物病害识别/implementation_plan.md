# 项目4：PlantVillage农作物病害识别 - 实施计划

## 1. 项目概述
**目标**：基于PlantVillage数据集（38类病害），构建高精度图像分类模型。
**时间**：第5-12周
**指标**：
- 基线（ResNet50）：验证准确率 ≥ 90%
- 优化后（EfficientNet/Focal Loss等）：验证准确率 ≥ 93%

## 2. 环境与数据准备 (当前阶段)
- [x] 克隆代码模板 `pytorch-image-classification`
- [x] **代码重构**：将Notebook转换为模块化项目 (`src/dataset.py`, `src/model.py`, `src/train.py`)
- [ ] **数据获取**：运行 `python download_data.py` 或手动下载 PlantVillage 数据集
- [ ] **数据预处理**：
  - [x] 编写 `dataset.py` 处理 `ImageFolder` 和 `random_split`
  - [x] 适配DataLoader (支持38个类别)

## 3. 基线模型实现 (第5-6周)
- [ ] **模型修改**：
  - 修改输出层为38类
  - 使用预训练ResNet50
- [ ] **训练配置**：
  - 基础数据增强 (Resize, RandomHorizontalFlip, Normalize)
  - 损失函数: CrossEntropyLoss
  - 优化器: Adam/SGD
- [ ] **验证**：达到90%准确率

## 4. 模型优化 (第7-8周)
- [ ] **高级数据增强**：
  - Mixup
  - CutMix
- [ ] **类别不平衡处理**：
  - 实现Focal Loss
- [ ] **模型架构对比**：
  - 引入EfficientNet (B0-B4)
- [ ] **验证**：达到93%准确率

## 5. 项目交付
- [ ] 整理代码结构
- [ ] 编写README文档
- [ ] 导出最佳模型权重
