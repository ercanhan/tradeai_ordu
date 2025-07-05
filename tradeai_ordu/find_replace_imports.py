import os
import re

PROJECT_ROOT = "./tradeai_ordu"  # Proje ana dizinini buraya yaz!

def has_config_usage(content):
    return re.search(r'\bConfig\.', content) is not None

def has_config_import(content):
    return "from config.config import Config" in content

def fix_config_import(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    fixed = False
    # Eğer Config kullanılıyor ama import yoksa başa import ekle
    if has_config_usage(content) and not has_config_import(content):
        lines = content.splitlines()
        # İlk importtan sonra ekle
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1
        lines.insert(insert_idx, "from config.config import Config")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"✔ Config importu eklendi: {filepath}")
        fixed = True
    return fixed

def scan_and_fix():
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                fix_config_import(filepath)

if __name__ == "__main__":
    scan_and_fix()
    print("Tüm dosyalarda Config importları otomatik eklendi Hünkar! 🔥")
