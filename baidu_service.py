import requests
from typing import Dict, Optional
from urllib.parse import quote


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
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == 0 and data.get("results"):
                return data["results"][0]
            return None
        except requests.RequestException:
            return None

    def geocode(self, address: str) -> Optional[Dict]:
        """
        地址解析为经纬度（百度地理编码），需要AK
        """
        if not self.api_key:
            return None

        url = f"{self.base_url}/geocoding/v3"
        params = {
            "address": address,
            "output": "json",
            "ak": self.api_key
        }
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == 0 and data.get("result"):
                return data["result"]
            return None
        except requests.RequestException:
            return None

    def get_current_location(self) -> Optional[Dict]:
        """
        通过IP定位获取当前坐标（需要AK）。
        返回统一结构的地点信息字典。
        """
        if not self.api_key:
            return None

        url = f"{self.base_url}/location/ip"
        params = {
            "ak": self.api_key,
            "coor": "bd09ll",
            "output": "json"
        }
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
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
            return None
        except requests.RequestException:
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
    若提供AK则尽量解析坐标；否则退化为名称直链。
    """
    service = BaiduLocationService(api_key)

    # 交通方式映射
    mode = BaiduTransportMode.DRIVING
    if transport_mode:
        t = transport_mode.lower()
        if t in ("driving", "car"):
            mode = BaiduTransportMode.DRIVING
        elif t in ("public_transit", "transit", "bus", "metro"):
            mode = BaiduTransportMode.PUBLIC_TRANSIT
        elif t in ("walking", "walk"):
            mode = BaiduTransportMode.WALKING

    # 起点
    if from_name in ["当前位置", "我的位置", "这里", ""]:
        from_info = service.get_current_location() if api_key else None
        if not from_info:
            from_info = {"name": "当前位置", "lnglat": ""}
    else:
        from_info = service.get_location_info(from_name, from_city)

    # 终点
    to_info = service.get_location_info(to_name, to_city)
    if not to_info:
        # 若完全失败，仍可用名称跳转
        to_info = {"name": to_name, "lnglat": ""}

    # 构造origin/destination部分
    def fmt(name: str, lnglat: str) -> str:
        name_q = quote(name or "")
        if lnglat:
            return f"{name_q}::{lnglat}"
        return name_q

    origin = fmt(from_info.get("name", from_name), from_info.get("lnglat", ""))
    dest = fmt(to_info.get("name", to_name), to_info.get("lnglat", ""))

    # 组合URL
    base = "https://map.baidu.com/direction"
    return f"{base}?origin={origin}&destination={dest}&mode={mode}"

