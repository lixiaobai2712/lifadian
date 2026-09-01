# -*- coding: utf-8 -*-
"""
批量采集多城市理发店 POI 并合并为总文件

功能：
  1. 从下方 CITY_LIST 中依次读取城市名称
  2. 对每个城市调用 gaode_barber_poi.py 采集脚本
  3. 每两个城市之间间隔 INTERVAL 秒（默认 10 秒）
  4. 全部采集完成后，合并所有生成的 CSV 文件为一个总文件
  5. 合并时保留全部字段，并在最后追加一列「来源城市」

用法：
  1. 把下方 CITY_LIST 改为你要采集的城市
  2. 在本目录运行：python batch_collect.py
  3. 汇总文件生成在脚本同目录：理发店汇总_YYYYMMDD.csv

注意：
  - 依赖 gaode_barber_poi.py 与本脚本放在同一目录
  - 每个城市单独生成一个 CSV（城市_理发店_日期.csv），合并时不会改动它们
"""

import os
import sys
import time
import csv
import subprocess
from datetime import datetime

# ================= 配置区 =================
# 【请替换为你的城市列表】在这里填入你要采集的城市，例如：
CITY_LIST = [
    "哈尔滨市",
    "齐齐哈尔市",
    "牡丹江市",
    "福州市",
]
INTERVAL = 10                       # 两个城市之间的间隔（秒）
COLLECT_SCRIPT = "gaode_barber_poi.py"      # 采集脚本文件名（须与本脚本同目录）
MERGE_FILENAME = "理发店汇总_{date}.csv"    # 合并总文件命名模板
# ==========================================


def run_one_city(city: str):
    """调用采集脚本采集单个城市，返回其产出的 CSV 文件名；失败返回 None。"""
    print(f"\n{'=' * 52}\n开始采集：{city}\n{'=' * 52}")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ret = subprocess.run(
        [sys.executable, COLLECT_SCRIPT, city],
        cwd=script_dir,
    )
    # 采集脚本的文件命名规则：{城市}_理发店_{日期}.csv
    today = datetime.now().strftime("%Y%m%d")
    filename = os.path.join(script_dir, f"{city}_理发店_{today}.csv")
    if ret.returncode != 0 or not os.path.exists(filename):
        print(f"[警告] {city} 采集未产出文件，跳过该城市。")
        return None
    return filename


def merge_csvs(file_city_pairs, out_filename: str) -> int:
    """合并所有 CSV：保留全部字段，在最后追加「来源城市」列，返回总记录数。"""
    merged = []
    fieldnames = None
    for filename, city in file_city_pairs:
        with open(filename, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames)  # 以第一个文件的字段为准
            for row in reader:
                row["来源城市"] = city
                merged.append(row)

    out_fieldnames = fieldnames + ["来源城市"]
    with open(out_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    return len(merged)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)   # 保证相对路径与采集脚本一致

    if not CITY_LIST:
        print("CITY_LIST 为空，请先在批处理脚本中填入要采集的城市。")
        return

    print(f"待采集城市 {len(CITY_LIST)} 个：{'、'.join(CITY_LIST)}")

    produced = []   # [(csv 文件路径, 来源城市), ...]
    total_cities = len(CITY_LIST)

    for i, city in enumerate(CITY_LIST):
        filename = run_one_city(city)
        if filename:
            produced.append((filename, city))

        # 每两个城市之间间隔 INTERVAL 秒（最后一个城市之后不再等待）
        if i < total_cities - 1:
            print(f"等待 {INTERVAL} 秒后采集下一个城市 ...")
            time.sleep(INTERVAL)

    if not produced:
        print("\n没有任何城市成功产出 CSV，未生成汇总文件。")
        return

    out_filename = MERGE_FILENAME.format(date=datetime.now().strftime("%Y%m%d"))
    total = merge_csvs(produced, out_filename)

    print(f"\n{'=' * 52}\n合并完成")
    print(f"  参与城市：{len(produced)} 个")
    for filename, city in produced:
        print(f"    {city}: {os.path.basename(filename)}")
    print(f"  总记录数：{total} 条")
    print(f"  已保存至：{os.path.join(script_dir, out_filename)}")


if __name__ == "__main__":
    main()
