# -*- coding: utf-8 -*-
"""
高德地图 POI 采集脚本 —— 理发店（按区县 × 关键词拆分采集）
功能：通过高德地图「地点搜索API」(/v3/place/text) 采集指定城市理发店类 POI，保存为 CSV。

背景说明（重要）：
  高德 /v3/place/text 对单个检索条件（关键词或城市）实际只返回前约 220 条
  （约 11 页，第 12 页起返回空；count 字段为估算值，不可作为翻页依据）。
  因此本脚本先按城市行政区域（区/县/县级市）拆分，再对每个关键词分别搜索，
  每个组合独立翻页至返回空为止，最后合并去重，以获得尽量完整的数据。

使用：
  1. 修改下方配置区中的 API_KEY（和可选 CITY）
  2. 安装依赖：pip install requests
  3. 运行：python gaode_barber_poi.py
"""

import sys
import time
import csv
import requests
from datetime import datetime
from typing import List, Dict, Optional

# ================= 配置区 =================
API_KEY = "18d9ee10f033718702481b776d9c884a"        # 高德开放平台申请的 Web 服务 Key
CITY = "哈尔滨市"                                   # 城市名称，如 "北京市" / "哈尔滨市" / "广州市"
KEYWORDS = ["理发店", "美发店", "造型工作室", "快剪", "男士理发馆"]   # 拆分后的单个关键词列表
OUTPUT_FIELDS = ["名称", "地址", "经纬度", "电话", "省份", "城市", "区县"]
# ==========================================

SEARCH_URL = "https://restapi.amap.com/v3/place/text"
DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
PAGE_SIZE = 20          # 每页条数（需求指定 20，高德上限 25）
REQUEST_INTERVAL = 0.5  # 两次请求之间的间隔（秒）
MAX_RETRY = 3           # 请求失败时的重试次数
MAX_PAGE = 100          # 单组合最大页数保险（正常会在返回空时提前停止）


def fetch_with_retry(url: str, params: dict) -> Optional[dict]:
    """发起一次请求，失败自动重试 MAX_RETRY 次。成功返回 JSON，彻底失败返回 None。"""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "1":
                return data
            print(f"  [第{attempt}次] API 返回业务错误：{data.get('info')}")
        except requests.RequestException as e:
            print(f"  [第{attempt}次] 网络/请求异常：{e}")
        if attempt < MAX_RETRY:
            time.sleep(2)
    return None


def get_districts(city: str) -> List[Dict[str, str]]:
    """通过行政区划 API 获取目标城市的全部区县（含县级市），返回 [{name, adcode}]。"""
    params = {
        "key": API_KEY,
        "keywords": city,
        "subdistrict": 2,
        "extensions": "base",
    }
    data = fetch_with_retry(DISTRICT_URL, params)
    if not data:
        return []
    districts = data.get("districts", [])
    if not districts:
        return []
    sub = districts[0].get("districts", [])
    result = [{"name": s.get("name", ""), "adcode": s.get("adcode", "")} for s in sub if s.get("adcode")]
    if not result:
        # 城市下无区县（如直辖市的某些情况），退化为直接用城市本身
        result = [{"name": districts[0].get("name", city), "adcode": districts[0].get("adcode", city)}]
    return result


def collect_pois(city: str) -> List[Dict[str, str]]:
    """按「区县 × 关键词」组合翻页采集，合并去重，返回整理好的 POI 列表。"""
    pois: List[Dict[str, str]] = []
    seen = set()   # 去重集合（按 poi id）
    districts = get_districts(city)
    if not districts:
        print("获取区县列表失败，无法拆分采集。")
        return pois

    print(f"共 {len(districts)} 个区县 × {len(KEYWORDS)} 个关键词 = "
          f"{len(districts) * len(KEYWORDS)} 个组合，开始采集 ...")

    for dist in districts:
        dname, dadcode = dist["name"], dist["adcode"]
        for kw in KEYWORDS:
            page = 1
            while True:
                params = {
                    "key": API_KEY,
                    "keywords": kw,
                    "city": dadcode,          # 用区县 adcode 精确限定范围
                    "citylimit": "true",
                    "offset": PAGE_SIZE,
                    "page": page,
                    "extensions": "base",
                }
                data = fetch_with_retry(SEARCH_URL, params)
                if data is None:
                    print(f"  [{dname} × {kw}] 第{page}页重试{MAX_RETRY}次仍失败，跳过该组合。")
                    break

                batch = data.get("pois", [])
                if not batch:                 # 翻到空页即停止该组合
                    break

                for poi in batch:
                    uid = poi.get("id") or (poi.get("name", "") + poi.get("location", ""))
                    if uid in seen:
                        continue              # 不同组合结果可能重复，去重
                    seen.add(uid)
                    pois.append({
                        "名称": poi.get("name", ""),
                        "地址": poi.get("address", ""),
                        "经纬度": poi.get("location", ""),   # 格式为 "经度,纬度"
                        "电话": poi.get("tel", ""),
                        "省份": poi.get("pname", ""),
                        "城市": poi.get("cityname", ""),
                        "区县": poi.get("adname", ""),
                    })

                if page >= MAX_PAGE:
                    break
                page += 1
                time.sleep(REQUEST_INTERVAL)  # 每页请求间隔 0.5 秒

        print(f"  完成区县 {dname}，累计 {len(pois)} 条")

    return pois


def save_to_csv(pois: List[Dict[str, str]], filename: str):
    """写入 CSV。使用 utf-8-sig 编码，保证 Excel 直接打开中文不乱码。"""
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(pois)


def main():
    if API_KEY == "【请替换为你的API Key】":
        print("请先在高德开放平台申请 Web 服务 Key，并填入配置区 API_KEY 变量！")
        return

    # 支持命令行指定城市：python gaode_barber_poi.py 齐齐哈尔市
    city = sys.argv[1] if len(sys.argv) > 1 else CITY

    print(f"开始采集 {city} 的理发店 POI ...")
    pois = collect_pois(city)

    if not pois:
        print("未采集到任何数据，请检查：城市名称 / API Key / 关键词是否有效。")
        return

    filename = f"{city}_理发店_{datetime.now().strftime('%Y%m%d')}.csv"
    save_to_csv(pois, filename)
    print(f"采集完成：共 {len(pois)} 条，已保存至 {filename}")


if __name__ == "__main__":
    main()
