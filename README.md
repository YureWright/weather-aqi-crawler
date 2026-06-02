# 空气质量与天气数据爬虫

从 [天气后报网](https://www.tianqihoubao.com) 爬取指定城市和年份的 AQI 与天气数据，合并后按固定列序导出为 Excel 文件。提供命令行和 Web 界面两种使用方式。

## 输出列序

城市、日期、年、月、日、质量等级、AQI、AQI排名、PM2.5、PM10、SO2、NO2、CO、O3、天气1、天气2、最低温、最高温、风向夜间、风力夜间、风向白天、风力白天

## 功能

- 爬取 50 个主要城市的 AQI 与逐日天气数据
- 支持多城市、多年份批量爬取
- 数据合并后按需求列序导出 `.xlsx`
- 请求间隔可调，避免被网站屏蔽
- Web 前端可视化操作：城市标签输入（支持逗号粘贴分隔）、年份多选、进度展示、结果下载
- 详细的运行日志和警告日志

## 快速开始

### 1. 安装

```bash
# 安装 Python 依赖
pip install flask pandas openpyxl playwright beautifulsoup4 lxml

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 命令行使用

```bash
# 爬取北京 2015 年的数据
python crawler.py --cities 北京 --years 2015

# 爬取多个城市、多年份
python crawler.py --cities 北京 天津 石家庄 --years 2015 2016 2017

# 指定输出目录
python crawler.py --cities 北京 --years 2015 --output ./my_data
```

输出文件位于 `output/` 目录（或指定目录），文件名格式：`空气质量与天气数据_YYYYMMDD_HHMMSS.xlsx`。

### 3. Web 界面使用

```bash
python app.py
```

打开浏览器访问 `http://127.0.0.1:5000`

操作步骤：
1. 在输入框中输入城市名（多个城市用逗号分隔，支持直接粘贴）
2. 勾选年份
3. 拖动滑块调整爬取间隔（间隔越大越安全，但越慢）
4. 点击"开始爬取"
5. 等待进度条完成，点击"下载"按钮获取 Excel

## 项目结构

```
├── app.py                  Flask Web 应用
├── crawler.py              核心爬虫（AQI + 天气）
├── city_map.py             城市名到拼音的映射表
├── config.py               日志路径配置
├── log.py                  日志器配置
├── templates/
│   └── index.html          Web 前端页面
├── output/                 爬取结果输出目录
├── log_and_warn/
│   ├── log/                运行日志
│   └── warnings/           警告日志
└── requirements.txt        Python 依赖
```

## 支持的城市

北京、上海、天津、重庆、哈尔滨、长春、沈阳、呼和浩特、石家庄、太原、西安、济南、乌鲁木齐、拉萨、西宁、兰州、银川、郑州、南京、武汉、杭州、合肥、福州、南昌、长沙、贵阳、成都、广州、昆明、南宁、深圳、鄂尔多斯、秦皇岛、张家口、青岛、唐山、开封、廊坊、衡水、许昌、保定、沧州、新乡、邢台、菏泽、淄博、邯郸、北京市、石家庄市、沧州市（含"市"后缀别名）

如需添加新城市，编辑 `city_map.py`，按格式添加 `"城市名": "拼音"` 即可。

## 注意

- 建议爬取间隔设为 2 秒以上，避免触发网站反爬机制
- 首次运行需要下载 Playwright 浏览器：`playwright install chromium`
- Flask 以 `debug=False` 运行，防止 reloader 导致任务状态丢失
- 洛阳在天气后报网无数据，无法支持
