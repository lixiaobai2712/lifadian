# -*- coding: utf-8 -*-
"""
数据清洗脚本 —— 理发店汇总数据

功能：
  1. 读取合并后的总 CSV 文件（理发店汇总_*.csv）
  2. 删除「名称」或「地址」为空的记录
  3. 去除名称、地址首尾及中间多余空格
  4. 电话统一格式：去掉空格、横杠、括号，只保留数字（多号码以分号分隔）
  5. 经纬度超出中国范围（经度73-135，纬度3-54）的记录单独写入「异常数据.csv」
  6. 清洗后的数据保存为「清洗后_店铺数据.csv」

用法：
  python clean_data.py [输入csv路径]
  不带参数时自动读取当前目录最新的「理发店汇总_*.csv」
"""

import csv
import re
import sys
import glob
import os

# ================= 配置区 =================
DEFAULT_PATTERN = "理发店汇总_*.csv"       # 自动匹配输入文件
OUTPUT_CLEAN = "清洗后_店铺数据.csv"        # 清洗后输出文件名
OUTPUT_ABNORMAL = "异常数据.csv"            # 异常数据输出文件名
CHINA_LNG_RANGE = (73, 135)                # 中国经度范围
CHINA_LAT_RANGE = (3, 54)                  # 中国纬度范围
# ==========================================

NAME_FIELD = "名称"
ADDR_FIELD = "地址"
PHONE_FIELD = "电话"
LOC_FIELD = "经纬度"


def clean_text(value) -> str:
    """去除首尾及中间多余空格（连续空白合并为一个空格）。"""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_phone(value) -> str:
    """电话统一为纯数字：去掉空格/横杠/括号等符号。

    若原字段含多个号码（以分号/逗号/空格等分隔），先拆分再逐个清洗，
    最后以分号连接，避免多个号码粘连成无法拨号的一长串。
    """
    if value is None:
        return ""
    parts = re.split(r"[;；,，/、\s]+", str(value))
    cleaned = []
    for part in parts:
        digits = re.sub(r"\D", "", part)   # 只保留数字
        if digits:
            cleaned.append(digits)
    return ";".join(cleaned)


def parse_location(value):
    """解析经纬度字段（格式：经度,纬度），成功返回 (lng, lat)，失败返回 None。"""
    if not value:
        return None
    parts = str(value).split(",")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def in_china(lng: float, lat: float) -> bool:
    """判断经纬度是否在中国范围内。"""
    return (CHINA_LNG_RANGE[0] <= lng <= CHINA_LNG_RANGE[1]
            and CHINA_LAT_RANGE[0] <= lat <= CHINA_LAT_RANGE[1])


def find_input_file():
    """返回指定的或最新的汇总 CSV 路径；未找到返回 None。"""
    if len(sys.argv) > 1:
        path = sys.argv[1]
        return path if os.path.exists(path) else None
    files = glob.glob(DEFAULT_PATTERN)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def main():
    input_file = find_input_file()
    if not input_file:
        print("未找到输入文件，请指定：python clean_data.py <输入csv路径>")
        return

    print(f"读取文件：{input_file}")

    cleaned_rows = []       # 清洗后数据
    abnormal_rows = []      # 异常数据
    removed_count = 0       # 因名称/地址为空删除的数量
    total_count = 0         # 原始总记录数

    with open(input_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)

        for row in reader:
            total_count += 1

            # 1) 删除「名称」或「地址」为空的记录
            name_raw = row.get(NAME_FIELD, "") or ""
            addr_raw = row.get(ADDR_FIELD, "") or ""
            if not name_raw.strip() or not addr_raw.strip():
                removed_count += 1
                continue

            # 2) 清洗名称、地址（去首尾及中间多余空格）
            row[NAME_FIELD] = clean_text(name_raw)
            row[ADDR_FIELD] = clean_text(addr_raw)

            # 3) 清洗电话（统一为纯数字）
            row[PHONE_FIELD] = clean_phone(row.get(PHONE_FIELD))

            # 4) 经纬度检查：无法解析或超出中国范围 → 异常数据
            loc = parse_location(row.get(LOC_FIELD))
            if loc is None:
                row["异常原因"] = "经纬度缺失或格式错误"
                abnormal_rows.append(row)
            elif not in_china(*loc):
                row["异常原因"] = (f"经纬度超出中国范围（当前: 经度{loc[0]}, "
                                   f"纬度{loc[1]}）")
                abnormal_rows.append(row)
            else:
                cleaned_rows.append(row)

    # 5) 保存清洗后数据（保留全部原字段）
    with open(OUTPUT_CLEAN, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    # 6) 保存异常数据（原字段 + 异常原因列）
    abnormal_fieldnames = fieldnames + ["异常原因"]
    with open(OUTPUT_ABNORMAL, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=abnormal_fieldnames)
        writer.writeheader()
        writer.writerows(abnormal_rows)

    # 统计输出
    print(f"原始总记录数：{total_count}")
    print(f"因名称/地址为空删除：{removed_count}")
    print(f"经纬度异常记录：{len(abnormal_rows)}")
    print(f"清洗后记录数：{len(cleaned_rows)}")
    print(f"已保存：{OUTPUT_CLEAN}（{len(cleaned_rows)} 条）")
    print(f"已保存：{OUTPUT_ABNORMAL}（{len(abnormal_rows)} 条）")


if __name__ == "__main__":
    main()
