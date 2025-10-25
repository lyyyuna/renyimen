import requests
from typing import Dict, Optional
from urllib.parse import quote
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaiduTransportMode:
    DRIVING = "driving"
    PUBLIC_TRANSIT = "transit"
    WALKING = "walking"


class BaiduLocationService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.map.baidu.com"

    def search_poi(self, keywords: str, city: str = None) -> Optional[Dict]:
        """
        通过关键字搜索POI（百度地点检索）
        需要AK（api_key）
        """
        if not self.api_key:
            logger.warning("未提供API密钥，无法执行POI搜索")
            return None

        url = f"{self.base_url}/place/v2/search"
        params = {
            "query": keywords,
            "region": city or "全国",
            "output": "json",
            "ak": self.api_key
        }
        try:
            resp = requests.get(url, params=params)
            logger.info("POI搜索请求URL：%s, 参数：%s", url, params)
            resp.raise_for_status()
            logger.info("POI搜索响应状态码：%s", resp.status_code)
            data = resp.json()
            if data.get("status") == 0 and data.get("results"):
                return data["results"][0]
            logger.warning("POI搜索无结果或状态异常：%s", data.get("status"))
            return None
        except requests.RequestException as e:
            logger.error("POI搜索请求失败：%s", str(e))
            return None

    def geocode(self, address: str) -> Optional[Dict]:
        """
        地址解析为经纬度（百度地理编码），需要AK
        """
        if not self.api_key:
            logger.warning("未提供API密钥，无法执行地理编码")
            return None

        url = f"{self.base_url}/geocoding/v3"
        params = {
            "address": address,
            "output": "json",
            "ak": self.api_key
        }
        try:
            resp = requests.get(url, params=params)
            logger.info("地理编码请求URL：%s, 参数：%s", url, params)
            resp.raise_for_status()
            logger.info("地理编码响应状态码：%s", resp.status_code)
            data = resp.json()
            if data.get("status") == 0 and data.get("result"):
                return data["result"]
            logger.warning("地理编码无结果或状态异常：%s", data.get("status"))
            return None
        except requests.RequestException as e:
            logger.error("地理编码请求失败：%s", str(e))
            return None

    def get_current_location(self) -> Optional[Dict]:
        """
        通过IP定位获取当前坐标（需要AK）。
        返回统一结构的地点信息字典。
        """
        if not self.api_key:
            logger.warning("未提供API密钥，无法获取当前位置")
            return None

        url = f"{self.base_url}/location/ip"
        params = {
            "ak": self.api_key,
            "coor": "bd09ll",
            "output": "json"
        }
        try:
            resp = requests.get(url, params=params)
            logger.info("IP定位请求URL：%s, 参数：%s", url, params)
            resp.raise_for_status()
            logger.info("IP定位响应状态码：%s", resp.status_code)
            data = resp.json()
            if data.get("status") == 0 and data.get("content"):
                point = data["content"].get("point", {})
                city = data["content"].get("address_detail", {}).get("city", "")
                lng = point.get("x", "")
                lat = point.get("y", "")
                return {
                    "id": "",
                    "name": "当前位置",
                    "lnglat": f"{lng},{lat}",
                    "modxy": f"{lng},{lat}",
                    "poitype": "",
                    "adcode": "",
                    "address": city,
                    "citycode": "",
                    "cityname": city,
                    "district": ""
                }
            logger.warning("IP定位无结果或状态异常：%s", data.get("status"))
            return None
        except requests.RequestException as e:
            logger.error("IP定位请求失败：%s", str(e))
            return None

    def get_location_info(self, location_name: str, city: str = None) -> Optional[Dict]:
        """
        获取地点统一信息结构：包含名称和经纬度等（优先检索，失败则地理编码）。
        """
        # 优先使用POI检索
        poi = self.search_poi(location_name, city)
        if poi:
            loc = poi.get("location", {})
            lng, lat = loc.get("lng"), loc.get("lat")
            if lng is not None and lat is not None:
                return {
                    "id": poi.get("uid", ""),
                    "name": poi.get("name", location_name),
                    "lnglat": f"{lng},{lat}",
                    "modxy": f"{lng},{lat}",
                    "poitype": poi.get("detail_info", {}).get("type", ""),
                    "adcode": "",
                    "address": poi.get("address", ""),
                    "citycode": "",
                    "cityname": city or "",
                    "district": ""
                }

        # 退化到地理编码
        geo = self.geocode(location_name)
        if geo and geo.get("location"):
            lng = geo["location"].get("lng")
            lat = geo["location"].get("lat")
            if lng is not None and lat is not None:
                return {
                    "id": "",
                    "name": location_name,
                    "lnglat": f"{lng},{lat}",
                    "modxy": f"{lng},{lat}",
                    "poitype": "",
                    "adcode": "",
                    "address": geo.get("formatted_address", ""),
                    "citycode": "",
                    "cityname": city or "",
                    "district": ""
                }

        # 若无AK或解析失败，返回仅含名称的结构（URL可用名称直接搜索）
        return {
            "id": "",
            "name": location_name,
            "lnglat": "",
            "modxy": "",
            "poitype": "",
            "adcode": "",
            "address": "",
            "citycode": "",
            "cityname": city or "",
            "district": ""
        }


def build_baidu_direction_url_from_names(api_key: str, from_name: str, to_name: str,
                                         from_city: str = None, to_city: str = None,
                                         transport_mode: str = None) -> Optional[str]:
    """
    通过起终点名称构建百度地图路线规划URL。
    若提供API密钥则尽量解析坐标；否则退化为名称直链。
    """
    # 打印输入参数
    logger.info(
        "构建百度地图导航URL，参数：api_key=%s, from_name=%s, to_name=%s, from_city=%s, to_city=%s, transport_mode=%s",
        "******" if api_key else None, from_name, to_name, from_city, to_city, transport_mode
    )

    service = BaiduLocationService(api_key)

    # 交通方式映射
    mode_map = {
        "driving": "0",  # 驾车
        "car": "0",
        "public_transit": "2",  # 公交
        "transit": "2",
        "bus": "2",
        "metro": "2",
        "walking": "3",  # 步行
        "walk": "3"
    }
    sy = mode_map.get(transport_mode.lower(), "0") if transport_mode else "0"
    logger.info("选择的交通方式（sy参数）：%s", sy)

    # 起点
    if from_name in ["当前位置", "我的位置", "这里", ""]:
        from_info = service.get_current_location() if api_key else None
        if not from_info:
            from_info = {"name": "我的位置", "lnglat": "", "cityname": from_city or "", "id": ""}
    else:
        from_info = service.get_location_info(from_name, from_city)
    logger.info("起点信息：%s", from_info)

    # 终点
    to_info = service.get_location_info(to_name, to_city)
    if not to_info:
        to_info = {"name": to_name, "lnglat": "", "cityname": to_city or "", "id": ""}
    logger.info("终点信息：%s", to_info)

    # 构造sn/en参数
    def fmt_node(info: Dict, default_name: str) -> str:
        name = quote(info.get("name", default_name) or "未知地点")
        lnglat = info.get("lnglat", "")
        uid = info.get("id", "")
        if lnglat:
            lng, lat = lnglat.split(",")
            return f"0$${uid}$${lng},{lat}$${name}$$$$"
        return f"0$${uid}$$${name}$$$$"

    sn = fmt_node(from_info, from_name)
    en = fmt_node(to_info, to_name)
    logger.info("起点参数（sn）：%s", sn)
    logger.info("终点参数（en）：%s", en)

    # 构造路径参数
    from_name_encoded = quote(from_info.get("name", from_name) or "我的位置")
    to_name_encoded = quote(to_info.get("name", to_name) or "未知地点")

    # 计算中心点和缩放级别
    center_lng, center_lat, zoom = 13528051.21, 3644599.15, "13z"  # 默认值
    if from_info.get("lnglat") and to_info.get("lnglat"):
        try:
            from_lng, from_lat = map(float, from_info["lnglat"].split(","))
            to_lng, to_lat = map(float, to_info["lnglat"].split(","))
            center_lng = (from_lng + to_lng) / 2
            center_lat = (from_lat + to_lat) / 2
            zoom = "13z"
        except ValueError:
            logger.warning("坐标解析失败，使用默认中心点")
    logger.info("地图中心点：@%s,%s,%s", center_lng, center_lat, zoom)

    # 组合URL
    base = f"https://map.baidu.com/dir/{from_name_encoded}/{to_name_encoded}/@{center_lng},{center_lat},{zoom}"
    params = {
        "querytype": "nav",
        "da_src": "shareurl",
        "navtp": "4",
        "c": "1",
        "sc": quote(from_city) if from_city else "1",
        "ec": quote(to_city) if to_city else "1",
        "sy": sy,
        "drag": "0",
        "sn": sn,
        "en": en,
        "sq": from_name_encoded,
        "eq": to_name_encoded,
        "version": "4",
        "mrs": "1",
        "route_traffic": "1"
    }

    # 构建查询字符串
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{base}?{query}"
    logger.info("生成的导航URL：%s", url)

    return url