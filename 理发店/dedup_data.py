# -*- coding: utf-8 -*-
"""
数据去重脚本 —— 清洗后店铺数据

功能：
  1. 读取「清洗后_店铺数据.csv」
  2. 以「名称 + 地址」作为判断重复的依据
  3. 出现重复时保留第一条
  4. 统计并打印：原始条数、去重后条数、删除的重复条数
  5. 去重后的数据保存为「去重后_店铺数据.csv」
  6. 被删除的重复记录单独保存为「重复记录备份.csv」，方便复核

用法：
  python dedup_data.py
"""

import csv

# ================= 配置区 =================
INPUT_FILE = "清洗后_店铺数据.csv"      # 输入文件
OUTPUT_DEDUP = "去重后_店铺数据.csv"     # 去重后输出
OUTPUT_BACKUP = "重复记录备份.csv"       # 重复记录备份
KEY_FIELDS = ("名称", "地址")            # 重复判断依据字段
# ==========================================


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            rows = list(reader)
    except FileNotFoundError:
        print(f"未找到输入文件：{INPUT_FILE}")
        return

    original_count = len(rows)

    seen = set()          # 已出现的 (名称, 地址) 键
    kept = []             # 去重后保留的数据
    duplicated = []       # 被删除的重复记录

    for row in rows:
        key = tuple((row.get(f) or "").strip() for f in KEY_FIELDS)
        if key in seen:
            duplicated.append(row)      # 重复：进入备份
        else:
            seen.add(key)
            kept.append(row)            # 首次出现：保留

    # 保存去重后数据（字段与输入一致）
    with open(OUTPUT_DEDUP, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    # 保存重复记录备份
    with open(OUTPUT_BACKUP, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(duplicated)

    # 统计输出
    print(f"原始条数：{original_count}")
    print(f"去重后条数：{len(kept)}")
    print(f"删除的重复条数：{len(duplicated)}")
    print(f"已保存：{OUTPUT_DEDUP}（{len(kept)} 条）")
    print(f"已保存：{OUTPUT_BACKUP}（{len(duplicated)} 条）")


if __name__ == "__main__":
    main()
