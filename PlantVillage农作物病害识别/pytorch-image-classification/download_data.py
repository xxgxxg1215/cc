"""
PlantVillage 数据集下载脚本

支持多种下载方式：
  1. Kaggle API（多个数据源自动切换）
  2. 手动下载指引

完整数据集包含 38 个类别，约 54,000 张图片。
"""

import os
import json
import shutil

# 项目根目录 & 数据目标路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
TARGET_DIR = os.path.join(DATA_DIR, "PlantVillage")

# 完整的 38 个类别列表
EXPECTED_CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

# Kaggle 数据集源（按优先级排序）
KAGGLE_DATASETS = [
    {
        "slug": "abdallahalidev/plantvillage-dataset",
        "description": "PlantVillage Dataset (abdallahalidev) - 包含 color/grayscale/segmented",
        "color_subdir": "plantvillage dataset/color",  # 彩色图片子目录
    },
    {
        "slug": "emmarex/plantdisease",
        "description": "Plant Disease (emmarex)",
        "color_subdir": None,
    },
    {
        "slug": "vipoooool/new-plant-diseases-dataset",
        "description": "New Plant Diseases Dataset (vipoooool) - 已分好 train/valid",
        "color_subdir": "New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/train",
    },
]


def setup_kaggle_credentials():
    """
    加载 Kaggle 凭证，按以下优先级：
      1. 项目目录下的 kaggle.json
      2. ~/.kaggle/kaggle.json
      3. 环境变量 KAGGLE_USERNAME / KAGGLE_KEY
      4. 交互式输入
    """
    # --- 1. 项目本地 kaggle.json（与脚本同目录） ---
    local_kaggle_json = os.path.join(SCRIPT_DIR, "kaggle.json")
    if os.path.exists(local_kaggle_json):
        try:
            with open(local_kaggle_json, "r", encoding="utf-8") as f:
                creds = json.load(f)
            username = creds.get("username", "").strip()
            key = creds.get("key", "").strip()
            if username and key:
                os.environ["KAGGLE_USERNAME"] = username
                os.environ["KAGGLE_KEY"] = key
                print(f"[OK] 从项目本地加载凭证: {local_kaggle_json}")
                return True
        except Exception as e:
            print(f"[WARN] 读取本地 kaggle.json 失败: {e}")

    # --- 2. 用户主目录 ~/.kaggle/kaggle.json ---
    home_kaggle_json = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
    if os.path.exists(home_kaggle_json):
        print(f"[OK] 检测到 Kaggle 凭证: {home_kaggle_json}")
        return True

    # --- 3. 环境变量 ---
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        print("[OK] 检测到 Kaggle 环境变量凭证")
        return True

    # --- 4. 交互式输入 ---
    print("=" * 60)
    print("未检测到 Kaggle 凭证。")
    print("获取步骤: https://www.kaggle.com/settings -> 'Create New Token'")
    print("下载的 kaggle.json 文件内容类似:")
    print('  {"username":"your_name","key":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}')
    print(f"你也可以直接把 kaggle.json 放到: {SCRIPT_DIR}")
    print("=" * 60)

    username = input("请输入 Kaggle Username (回车跳过): ").strip()
    if not username:
        return False
    key = input("请输入 Kaggle Key: ").strip()
    if not key:
        return False

    os.environ["KAGGLE_USERNAME"] = username
    os.environ["KAGGLE_KEY"] = key
    print("凭证已设置为本次会话环境变量。")
    return True


def find_image_dirs(root):
    """
    在 root 下递归查找包含图片文件的叶子目录。
    返回 {类别名: 目录路径} 的字典。
    """
    img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
    result = {}
    for dirpath, dirnames, filenames in os.walk(root):
        has_images = any(
            os.path.splitext(f)[1].lower() in img_exts for f in filenames
        )
        if has_images:
            class_name = os.path.basename(dirpath)
            if class_name not in result:
                result[class_name] = dirpath
    return result


def reorganize_to_target(source_root, target_dir):
    """
    将 source_root 下发现的图片类别目录整理到 target_dir 中。
    如果目标已存在同名文件夹则合并（跳过重复文件）。
    返回最终类别数量。
    """
    class_dirs = find_image_dirs(source_root)
    if not class_dirs:
        print(f"  [WARN] 在 {source_root} 下未发现包含图片的目录")
        return 0

    os.makedirs(target_dir, exist_ok=True)
    count = 0
    for class_name, src_path in class_dirs.items():
        dst_path = os.path.join(target_dir, class_name)
        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            count += 1
            continue
        if os.path.exists(dst_path):
            # 合并：逐文件复制
            for fname in os.listdir(src_path):
                src_file = os.path.join(src_path, fname)
                dst_file = os.path.join(dst_path, fname)
                if os.path.isfile(src_file) and not os.path.exists(dst_file):
                    shutil.copy2(src_file, dst_file)
        else:
            shutil.copytree(src_path, dst_path)
        count += 1

    return count


def verify_dataset(target_dir):
    """验证数据集完整性。返回 (是否完整, 已有类别列表, 缺失类别列表)。"""
    if not os.path.isdir(target_dir):
        return False, [], EXPECTED_CLASSES[:]

    existing = set()
    for d in os.listdir(target_dir):
        full = os.path.join(target_dir, d)
        if os.path.isdir(full):
            # 检查是否有图片
            img_count = 0
            for f in os.listdir(full):
                ext = os.path.splitext(f)[1].lower()
                if ext in {".jpg", ".jpeg", ".png", ".bmp"}:
                    img_count += 1
            if img_count > 0:
                existing.add(d)

    # 用模糊匹配对比（不同数据源的类别名可能有细微差异）
    missing = []
    for cls in EXPECTED_CLASSES:
        # 标准化比较
        cls_norm = cls.lower().replace(" ", "").replace("_", "").replace(",", "")
        found = False
        for e in existing:
            e_norm = e.lower().replace(" ", "").replace("_", "").replace(",", "")
            if cls_norm == e_norm or cls_norm in e_norm or e_norm in cls_norm:
                found = True
                break
        if not found:
            missing.append(cls)

    is_complete = len(existing) >= 38 or len(missing) == 0
    return is_complete, sorted(existing), missing


def download_via_kaggle(dataset_info, download_dir):
    """使用 Kaggle API 下载指定数据集。返回是否成功。"""
    slug = dataset_info["slug"]
    print(f"\n>>> 尝试下载: {dataset_info['description']}")
    print(f"    Kaggle slug: {slug}")

    try:
        import kaggle
        kaggle.api.authenticate()
    except ImportError:
        print("  [ERROR] kaggle 库未安装，请运行: pip install kaggle")
        return False
    except Exception as e:
        print(f"  [ERROR] Kaggle 认证失败: {e}")
        return False

    temp_dir = os.path.join(download_dir, "_kaggle_temp")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        print(f"  正在下载 (可能需要较长时间，请耐心等待)...")
        kaggle.api.dataset_download_files(slug, path=temp_dir, unzip=True)
        print("  下载并解压完成。")

        # 确定图片所在子目录
        color_subdir = dataset_info.get("color_subdir")
        if color_subdir:
            source = os.path.join(temp_dir, color_subdir)
            if not os.path.isdir(source):
                # 尝试在下载目录中搜索
                print(f"  预期子目录不存在: {color_subdir}")
                print(f"  将在整个下载目录中搜索图片...")
                source = temp_dir
        else:
            source = temp_dir

        # 整理到目标目录
        print(f"  正在整理数据到 {TARGET_DIR} ...")
        num_classes = reorganize_to_target(source, TARGET_DIR)
        print(f"  整理完成，发现 {num_classes} 个类别目录。")

        return num_classes > 0

    except Exception as e:
        print(f"  [ERROR] 下载失败: {e}")
        return False
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            print("  正在清理临时文件...")
            shutil.rmtree(temp_dir, ignore_errors=True)


def print_manual_instructions():
    """打印手动下载指引。"""
    print("\n" + "=" * 60)
    print("自动下载失败，请手动下载数据集：")
    print("=" * 60)
    print()
    print("推荐数据源（任选其一）：")
    print()
    print("1. [推荐] abdallahalidev/plantvillage-dataset")
    print("   https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset")
    print("   下载后将 color 文件夹内的所有类别目录复制到:")
    print(f"   {TARGET_DIR}")
    print()
    print("2. emmarex/plantdisease")
    print("   https://www.kaggle.com/datasets/emmarex/plantdisease")
    print("   下载后将所有类别目录复制到:")
    print(f"   {TARGET_DIR}")
    print()
    print("3. vipoooool/new-plant-diseases-dataset")
    print("   https://www.kaggle.com/datasets/vipoooool/new-plant-diseases-dataset")
    print("   下载后将 train 文件夹内的所有类别目录复制到:")
    print(f"   {TARGET_DIR}")
    print()
    print("最终目录结构应为：")
    print(f"  {TARGET_DIR}/")
    print(f"    ├── Apple___Apple_scab/")
    print(f"    │   ├── image1.JPG")
    print(f"    │   └── ...")
    print(f"    ├── Apple___Black_rot/")
    print(f"    │   └── ...")
    print(f"    ├── ... (共 38 个类别文件夹)")
    print(f"    └── Tomato___healthy/")
    print(f"        └── ...")
    print()
    print("也可以用 kaggle CLI 命令下载：")
    print("  pip install kaggle")
    print("  kaggle datasets download -d abdallahalidev/plantvillage-dataset")
    print("=" * 60)


def main():
    print("PlantVillage 农作物病害数据集下载工具")
    print(f"目标路径: {TARGET_DIR}")
    print(f"预期类别数: {len(EXPECTED_CLASSES)}")
    print()

    # 先检查现有数据
    is_complete, existing, missing = verify_dataset(TARGET_DIR)
    if is_complete:
        print(f"[OK] 数据集已完整！共 {len(existing)} 个类别。")
        return

    if existing:
        print(f"当前已有 {len(existing)} 个类别，缺少 {len(missing)} 个。")
        print(f"缺少的类别: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    else:
        print("当前无数据，将下载完整数据集。")

    # 尝试 Kaggle API 下载
    os.makedirs(DATA_DIR, exist_ok=True)
    has_credentials = setup_kaggle_credentials()

    if has_credentials:
        for ds_info in KAGGLE_DATASETS:
            success = download_via_kaggle(ds_info, DATA_DIR)
            if success:
                # 重新验证
                is_complete, existing, missing = verify_dataset(TARGET_DIR)
                print(f"\n当前状态: {len(existing)} 个类别")
                if is_complete:
                    print(f"[OK] 数据集完整！共 {len(existing)} 个类别。")
                    break
                else:
                    print(f"还缺少 {len(missing)} 个类别，尝试下一个数据源...")
            else:
                print("  该数据源下载失败，尝试下一个...")

        # 最终验证
        is_complete, existing, missing = verify_dataset(TARGET_DIR)
        if is_complete:
            print(f"\n{'='*60}")
            print(f"下载完成！共 {len(existing)} 个类别。")
            print(f"数据路径: {TARGET_DIR}")
            print(f"{'='*60}")
            return
        elif existing:
            print(f"\n[WARN] 下载了 {len(existing)} 个类别，但仍缺少 {len(missing)} 个。")
            print(f"缺少: {missing}")

    # 全部失败，打印手动指引
    print_manual_instructions()


if __name__ == "__main__":
    main()
