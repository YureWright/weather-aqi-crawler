"""
城市名称与中国拼音映射表
数据来源：从 https://www.tianqihoubao.com 网站提取的主要城市映射
"""

# 城市中文名 → 网站使用的拼音（用于构建 URL）
CITY_TO_PINYIN = {
    "北京": "beijing",
    "上海": "shanghai",
    "天津": "tianjin",
    "重庆": "chongqing",
    "哈尔滨": "haerbin",
    "长春": "changchun",
    "沈阳": "shenyang",
    "呼和浩特": "huhehaote",
    "石家庄": "shijiazhuang",
    "太原": "taiyuan",
    "西安": "xian",
    "济南": "jinan",
    "乌鲁木齐": "wulumuqi",
    "拉萨": "lasa",
    "西宁": "xining",
    "兰州": "lanzhou",
    "银川": "yinchuan",
    "郑州": "zhengzhou",
    "南京": "nanjing",
    "武汉": "wuhan",
    "杭州": "hangzhou",
    "合肥": "hefei",
    "福州": "fujianfuzhou",
    "南昌": "nanchang",
    "长沙": "changsha",
    "贵阳": "guiyang",
    "成都": "chengdu",
    "广州": "guangzhou",
    "昆明": "kunming",
    "南宁": "nanning",
    "深圳": "shenzhen",
    "鄂尔多斯": "eerduosi",
    "秦皇岛": "qinhuangdao",
    "张家口": "zhangjiakou",
    "青岛": "qingdao",
    "唐山": "tangshan",
    "开封": "kaifeng",
    "廊坊": "langfang",
    "衡水": "hengshui",
    "许昌": "xuchang",
    "保定": "baoding",
    "沧州": "cangzhou",
    "新乡": "xinxiang",
    "邢台": "xingtai",
    "菏泽": "heze",
    "淄博": "zibo",
    "邯郸": "handan",
    "洛阳": "lvyang",
    "枣庄": "zaozhuang",
    "承德": "chengde",
    "北京市": "beijing",
    "石家庄市": "shijiazhuang",
    "沧州市": "cangzhou",
}

# 反向映射：拼音 → 中文名
PINYIN_TO_CITY = {v: k for k, v in CITY_TO_PINYIN.items()}

# 网站 AQI 主要城市列表（用于参考）
MAJOR_CITIES = list(CITY_TO_PINYIN.keys())
