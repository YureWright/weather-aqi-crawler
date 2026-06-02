"""
空气质量与天气数据爬虫
数据来源：
  - AQI: https://www.tianqihoubao.com/aqi/
  - 天气: https://www.tianqihoubao.com/lishi/
输出格式：xlsx，按需求字段顺序排列
"""

import re
import time
import os
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright

from city_map import CITY_TO_PINYIN
import config
import log

# 获取日志器
logger = log.run_logger
warn_logger = log.warning_logger


# ============================================================
# 工具函数
# ============================================================

def build_aqi_url(city_pinyin: str, year: int, month: int) -> str:
    """构建 AQI 页面 URL"""
    return f"https://www.tianqihoubao.com/aqi/{city_pinyin}-{year}{month:02d}.html"


def build_weather_url(city_pinyin: str, year: int, month: int) -> str:
    """构建天气页面 URL"""
    return f"https://www.tianqihoubao.com/lishi/{city_pinyin}/month/{year}{month:02d}.html"


def parse_date(date_str: str) -> tuple:
    """
    解析日期字符串，返回 (年, 月, 日)
    支持格式: '2015-01-01' 或 '2015年01月01日'
    """
    date_str = date_str.strip()
    if '-' in date_str:
        parts = date_str.split('-')
        return int(parts[0]), int(parts[1]), int(parts[2])
    elif '年' in date_str:
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
    raise ValueError(f"无法解析日期: {date_str}")


def split_wind(wind_str: str) -> tuple:
    """
    解析风向风力字符串，返回 (风向, 风力)
    输入示例: '西北风 3-4级', '北风 ≤3级', '东风 3-4级'
    """
    wind_str = wind_str.strip()
    # 匹配模式：方向词 + 空格 + 风力等级
    match = re.match(r'([\u4e00-\u9fff]+风)\s*([\d\-\<\>\≤\u4e00-\u9fff级]+)', wind_str)
    if match:
        return match.group(1), match.group(2)
    # 如果解析失败，返回原字符串和空
    warn_logger.warning(f"风向风力解析失败: '{wind_str}'")
    return wind_str, ""


# ============================================================
# AQI 数据爬取与解析
# ============================================================

def parse_aqi_table(page_source: str, city_name: str, year: int, month: int) -> list[dict]:
    """
    解析 AQI 页面中的表格数据
    返回字段: 城市, 日期, 年, 月, 日, 质量等级, AQI, AQI排名, PM2.5, PM10, SO2, NO2, CO, O3
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')

    # 找到 AQI 数据表格
    table = soup.select_one('div.api_month_list table.b')
    if not table:
        warn_logger.warning(f"AQI表格未找到: {city_name} {year}-{month:02d}")
        return []

    rows = table.find_all('tr')
    records = []

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 10:
            continue

        # 跳过表头行
        first_text = cells[0].get_text(strip=True)
        if first_text == '日期' or not first_text:
            continue

        # 提取原始数据
        date_str = cells[0].get_text(strip=True)          # 日期
        aqi = cells[1].get_text(strip=True)               # AQI指数
        quality = cells[2].get_text(strip=True)            # 质量等级
        aqi_rank = cells[3].get_text(strip=True)           # 当天AQI排名
        pm25 = cells[4].get_text(strip=True)               # PM2.5
        pm10 = cells[5].get_text(strip=True)               # PM10
        no2 = cells[6].get_text(strip=True)                # NO2 (网站列名No2)
        so2 = cells[7].get_text(strip=True)                # SO2 (网站列名So2)
        co = cells[8].get_text(strip=True)                 # CO
        o3 = cells[9].get_text(strip=True)                 # O3

        try:
            y, m, d = parse_date(date_str)
        except ValueError as e:
            warn_logger.warning(f"日期解析失败: {e}")
            continue

        # 组装字段（按需求列序的子集：AQI相关字段）
        record = {
            "城市": city_name,
            "日期": f"{y}/{m}/{d}",
            "年": y,
            "月": m,
            "日": d,
            "质量等级": quality,
            "AQI": aqi,
            "AQI排名": aqi_rank,
            "PM2.5": pm25,
            "PM10": pm10,
            "SO2": so2,
            "NO2": no2,
            "CO": co,
            "O3": o3,
        }
        records.append(record)

    logger.info(f"AQI数据解析完成: {city_name} {year}-{month:02d}, 共 {len(records)} 条记录")
    return records


def scrape_aqi_month(city_name: str, city_pinyin: str, year: int, month: int,
                     browser_page) -> list[dict]:
    """
    爬取指定城市、年月 的 AQI 数据
    """
    url = build_aqi_url(city_pinyin, year, month)
    logger.info(f"开始爬取AQI: {url}")

    try:
        browser_page.goto(url, timeout=30000, wait_until='networkidle')
        time.sleep(0.2)  # 等待渲染完成
        page_source = browser_page.content()
        records = parse_aqi_table(page_source, city_name, year, month)
        logger.info(f"AQI爬取成功: {city_name} {year}-{month:02d}, {len(records)}条")
        return records
    except Exception as e:
        warn_logger.error(f"AQI爬取失败 [{url}]: {e}")
        return []


def scrape_aqi_year(city_name: str, city_pinyin: str, year: int,
                    browser_page) -> list[dict]:
    """爬取指定城市、整年的 AQI 数据（1月~12月）"""
    all_records = []
    for month in range(1, 13):
        month_records = scrape_aqi_month(city_name, city_pinyin, year, month, browser_page)
        all_records.extend(month_records)
    logger.info(f"AQI全年爬取完成: {city_name} {year}, 共 {len(all_records)} 条记录")
    return all_records


# ============================================================
# 天气数据爬取与解析
# ============================================================

def parse_weather_table(page_source: str, city_name: str, year: int, month: int) -> list[dict]:
    """
    解析天气页面中的表格数据
    返回字段: 城市, 日期, 年, 月, 日, 天气1(白天), 天气2(夜间),
              最低温, 最高温, 风向夜间, 风力夜间, 风向白天, 风力白天
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')

    # 找到天气数据表格
    table = soup.select_one('table.weather-table')
    if not table:
        warn_logger.warning(f"天气表格未找到: {city_name} {year}-{month:02d}")
        return []

    # 取 tbody 或直接用 tr
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
    else:
        rows = table.find_all('tr')

    records = []

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue

        # 跳过广告插入行（含 colspan 属性）
        if any(cell.get('colspan') for cell in cells):
            continue

        # 跳过空行
        first_cell_text = cells[0].get_text(strip=True)
        if not first_cell_text:
            continue

        # 日期从 <a> 标签中提取
        date_link = cells[0].find('a')
        if date_link:
            date_str = date_link.get_text(strip=True)
        else:
            date_str = first_cell_text

        try:
            y, m, d = parse_date(date_str)
        except ValueError as e:
            warn_logger.warning(f"日期解析失败: {e}")
            continue

        # 解析天气：天气状况(白天/夜间) → 天气1(白天), 天气2(夜间)
        weather_text = cells[1].get_text(strip=True)
        weather_parts = [w.strip() for w in weather_text.split('/')]
        weather_day = weather_parts[0] if len(weather_parts) > 0 else ""
        weather_night = weather_parts[1] if len(weather_parts) > 1 else ""

        # 解析温度：最高/最低气温
        temp_high_span = cells[2].find('span', class_='temp-high')
        temp_low_span = cells[2].find('span', class_='temp-low')
        if temp_high_span:
            temp_high = temp_high_span.get_text(strip=True).replace('℃', '')
        else:
            # fallback: 从完整文本提取
            temp_text = cells[2].get_text(strip=True)
            temp_parts = re.findall(r'(-?\d+)℃', temp_text)
            temp_high = temp_parts[0] if len(temp_parts) > 0 else ""
            temp_low = temp_parts[1] if len(temp_parts) > 1 else ""
            if temp_high_span:
                temp_high = temp_high_span.get_text(strip=True).replace('℃', '')
                temp_low = temp_low_span.get_text(strip=True).replace('℃', '') if temp_low_span else temp_low

        if temp_low_span:
            temp_low = temp_low_span.get_text(strip=True).replace('℃', '')
        else:
            temp_low = ""

        # 解析风向风力：风力风向(白天/夜间)
        wind_text = cells[3].get_text(strip=True)
        wind_parts = [w.strip() for w in wind_text.split('/')]

        wind_day_str = wind_parts[0] if len(wind_parts) > 0 else ""
        wind_night_str = wind_parts[1] if len(wind_parts) > 1 else ""

        wind_day_dir, wind_day_power = split_wind(wind_day_str)
        wind_night_dir, wind_night_power = split_wind(wind_night_str)

        record = {
            "城市": city_name,
            "日期": f"{y}/{m}/{d}",
            "年": y,
            "月": m,
            "日": d,
            "天气1": weather_day,
            "天气2": weather_night,
            "最低温": temp_low,
            "最高温": temp_high,
            "风向夜间": wind_night_dir,
            "风力夜间": wind_night_power,
            "风向白天": wind_day_dir,
            "风力白天": wind_day_power,
        }
        records.append(record)

    logger.info(f"天气数据解析完成: {city_name} {year}-{month:02d}, 共 {len(records)} 条记录")
    return records


def scrape_weather_month(city_name: str, city_pinyin: str, year: int, month: int,
                         browser_page) -> list[dict]:
    """爬取指定城市、年月的天气数据"""
    url = build_weather_url(city_pinyin, year, month)
    logger.info(f"开始爬取天气: {url}")

    try:
        browser_page.goto(url, timeout=30000, wait_until='networkidle')
        time.sleep(0.2)
        page_source = browser_page.content()
        records = parse_weather_table(page_source, city_name, year, month)
        logger.info(f"天气爬取成功: {city_name} {year}-{month:02d}, {len(records)}条")
        return records
    except Exception as e:
        warn_logger.error(f"天气爬取失败 [{url}]: {e}")
        return []


def scrape_weather_year(city_name: str, city_pinyin: str, year: int,
                        browser_page) -> list[dict]:
    """爬取指定城市、整年的天气数据（1月~12月）"""
    all_records = []
    for month in range(1, 13):
        month_records = scrape_weather_month(city_name, city_pinyin, year, month, browser_page)
        all_records.extend(month_records)
    logger.info(f"天气全年爬取完成: {city_name} {year}, 共 {len(all_records)} 条记录")
    return all_records


# ============================================================
# 数据合并与导出
# ============================================================

COLUMN_ORDER = [
    "城市", "日期", "年", "月", "日",
    "质量等级", "AQI", "AQI排名", "PM2.5", "PM10", "SO2", "NO2", "CO", "O3",
    "天气1", "天气2", "最低温", "最高温",
    "风向夜间", "风力夜间", "风向白天", "风力白天",
]


def merge_and_reorder(aqi_records: list[dict], weather_records: list[dict]) -> pd.DataFrame:
    """
    按日期合并 AQI 和天气数据，并按 COLUMN_ORDER 排列列序
    """
    df_aqi = pd.DataFrame(aqi_records) if aqi_records else pd.DataFrame()
    df_weather = pd.DataFrame(weather_records) if weather_records else pd.DataFrame()

    if df_aqi.empty and df_weather.empty:
        return pd.DataFrame(columns=COLUMN_ORDER)

    if df_aqi.empty:
        # 仅有天气数据，补充缺失的AQI列
        for col in COLUMN_ORDER:
            if col not in df_weather.columns:
                df_weather[col] = ""
        return df_weather[COLUMN_ORDER]

    if df_weather.empty:
        # 仅有AQI数据，补充缺失的天气列
        for col in COLUMN_ORDER:
            if col not in df_aqi.columns:
                df_aqi[col] = ""
        return df_aqi[COLUMN_ORDER]

    # 两者都有，按 城市+日期 合并
    merge_keys = ["城市", "日期", "年", "月", "日"]
    # 取出共有键列
    df_merged = df_aqi[merge_keys].copy()
    # 添加AQI相关列（排除已存在的键列）
    aqi_cols = [c for c in df_aqi.columns if c not in merge_keys]
    weather_cols = [c for c in df_weather.columns if c not in merge_keys]

    df_merged = pd.merge(
        df_aqi[merge_keys + aqi_cols],
        df_weather[merge_keys + weather_cols],
        on=merge_keys, how='outer'
    )

    # 填充缺失列
    for col in COLUMN_ORDER:
        if col not in df_merged.columns:
            df_merged[col] = ""

    # 按日期排序
    df_merged["_sort_date"] = pd.to_datetime(df_merged["日期"])
    df_merged = df_merged.sort_values("_sort_date").drop(columns=["_sort_date"])

    return df_merged[COLUMN_ORDER]


def export_to_xlsx(df: pd.DataFrame, output_path: str):
    """导出 DataFrame 到 xlsx 文件"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    df.to_excel(output_path, index=False, sheet_name="数据")
    logger.info(f"Excel 导出成功: {output_path}")


# ============================================================
# 批量爬取
# ============================================================

def batch_scrape(city_year_list: list[tuple], output_dir: str = "output",
                 sleep_interval: float = 0.2,
                 progress_callback: callable = None) -> pd.DataFrame:
    """
    批量爬取多城市、多年份数据

    参数:
        city_year_list: [(城市名, 年份), ...] 例如 [("北京", 2015), ("天津", 2016)]
        output_dir: 输出目录
        sleep_interval: 每次请求后的休眠间隔（秒）
        progress_callback: 进度回调函数，参数 (task_index, total_tasks, message)

    返回:
        合并后的全量 DataFrame
    """
    # 校验城市名
    for city_name, year in city_year_list:
        if city_name not in CITY_TO_PINYIN:
            raise ValueError(f"不支持的城市: {city_name}，可用城市: {list(CITY_TO_PINYIN.keys())}")

    all_data = pd.DataFrame()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        page = context.new_page()
        # 反检测：隐藏自动化特征
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        for idx, (city_name, year) in enumerate(city_year_list):
            city_pinyin = CITY_TO_PINYIN[city_name]
            msg = f"===== 开始爬取: {city_name} {year}年 ====="
            logger.info(msg)
            if progress_callback:
                progress_callback(idx, len(city_year_list), f"正在爬取 {city_name} {year}年（AQI）...")

            # 爬取 AQI 数据
            aqi_records = scrape_aqi_year(city_name, city_pinyin, year, page)

            if progress_callback:
                progress_callback(idx, len(city_year_list), f"正在爬取 {city_name} {year}年（天气）...")

            # 爬取天气数据
            weather_records = scrape_weather_year(city_name, city_pinyin, year, page)

            # 合并
            df_city = merge_and_reorder(aqi_records, weather_records)
            all_data = pd.concat([all_data, df_city], ignore_index=True)

            logger.info(f"===== {city_name} {year}年完成，共 {len(df_city)} 条 =====")
            if progress_callback:
                progress_callback(idx + 1, len(city_year_list),
                                  f"✅ {city_name} {year}年完成（{len(df_city)}条）")
            time.sleep(sleep_interval)  # 请求间隔，避免被屏蔽

        browser.close()

    # 去重
    all_data = all_data.drop_duplicates(subset=["城市", "日期"])

    # 导出
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"空气质量与天气数据_{timestamp}.xlsx")
    export_to_xlsx(all_data, output_file)

    return all_data, output_file


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="空气质量与天气数据爬虫")
    parser.add_argument("--cities", "-c", nargs="+", required=True,
                        help="城市名列表，例如: 北京 天津 上海")
    parser.add_argument("--years", "-y", nargs="+", type=int, required=True,
                        help="年份列表，例如: 2015 2016 2017")
    parser.add_argument("--output", "-o", default="output",
                        help="输出目录（默认: output）")

    args = parser.parse_args()

    city_year_list = [(city, year) for city in args.cities for year in args.years]

    logger.info(f"爬虫启动，参数: 城市={args.cities}, 年份={args.years}")
    logger.info(f"共 {len(city_year_list)} 个任务")

    df, out_file = batch_scrape(city_year_list, args.output)

    logger.info(f"爬虫完成！共导出 {len(df)} 条记录到 {out_file}")


if __name__ == "__main__":
    main()
