# -*- coding: utf-8 -*-
"""
生成 HivePress 可直接导入的 CSV

功能：
  1. 读取「去重后_店铺数据.csv」
  2. 将「经纬度」（格式 经度,纬度）拆分为「经度」「纬度」两列
  3. 按 HivePress 字段映射重排列（名称/地址/经度/纬度/电话/省份/城市/区县）
  4. 去掉仅用于复核的「来源城市」列
  5. 输出 hivepress_导入_YYYYMMDD.csv（utf-8-sig，Excel 打开不乱码）

导入说明（配合 HivePress 官方 Import Listings 功能）：
  - 在导入第二步映射界面，把每列拖到对应字段：
      名称 → Title（标题）
      地址 → Location（位置文本）
      经度 → Longitude（经度）
      纬度 → Latitude（纬度）
      电话 → Phone（需先在后台创建 slug=phone 的字段）
      城市 → City（需先创建 slug=city 的字段）
      区县 → District（需先创建 slug=district 的字段）
      省份 → State（可选，需先创建 slug=state 的字段）
  - 建议先导入 5~10 条验证，再全量导入

用法：
  python prepare_hivepress_csv.py
"""

import csv
import os
from datetime import datetime

# ================= 配置区 =================
INPUT_FILE = "去重后_店铺数据.csv"        # 输入文件
OUTPUT_PREFIX = "hivepress_导入"         # 输出文件名前缀
LOC_FIELD = "经纬度"                     # 原始经纬度列名
DROPPED_FIELDS = ["来源城市"]            # 不需要导入的辅助列
OUTPUT_FIELDS = ["名称", "地址", "经度", "纬度", "电话", "省份", "城市", "区县"]
# ==========================================


def split_location(loc_value):
    """把 '经度,纬度' 拆成 (经度, 纬度)；无法解析返回 ("", "")。"""
    if not loc_value:
        return "", ""
    parts = str(loc_value).split(",")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", ""


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"未找到输入文件：{INPUT_FILE}")
        return

    rows = []
    with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lng, lat = split_location(row.get(LOC_FIELD))
            new_row = {
                "名称": row.get("名称", ""),
                "地址": row.get("地址", ""),
                "经度": lng,
                "纬度": lat,
                "电话": row.get("电话", ""),
                "省份": row.get("省份", ""),
                "城市": row.get("城市", ""),
                "区县": row.get("区县", ""),
            }
            rows.append(new_row)

    out_filename = f"{OUTPUT_PREFIX}_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(out_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # 统计
    no_lng = sum(1 for r in rows if not r["经度"] or not r["纬度"])
    print(f"原始条数：{len(rows)}")
    print(f"经纬度无法拆分的记录：{no_lng}")
    print(f"输出字段：{'、'.join(OUTPUT_FIELDS)}")
    print(f"已保存：{out_filename}（{len(rows)} 条）")


if __name__ == "__main__":
    main()
