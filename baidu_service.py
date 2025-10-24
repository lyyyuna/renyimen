import requests
from typing import Dict, Optional
from urllib.parse import urlencode, quote


class BaiduLocationService:
    def __init__(self, ak: str):
        self.ak = ak
        self.place_base_url = "https://api.map.baidu.com/place/v2"
        self.geocode_url = "https://api.map.baidu.com/geocoding/v3/"

    def search_poi(self, keywords: str, region: str = None) -> Optional[Dict]:
        """
        通过关键词搜索POI信息（百度地点检索）

        Args:
            keywords: 搜索关键词（地点名称）
            region: 搜索区域（城市名，可选）

        Returns:
            返回第一条匹配的POI信息字典
        """
        url = f"{self.place_base_url}/search"
        params = {
            "query": keywords,
            "output": "json",
            "ak": self.ak,
        }
        if region:
            params["region"] = region

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results") or data.get("poi")
            if results:
                return results[0]
            else:
                print(f"百度POI搜索失败: {data.get('message') or data.get('msg') or '未知错误'}")
                return None
        except requests.RequestException as e:
            print(f"请求错误: {e}")
            return None

    def geocode(self, address: str) -> Optional[Dict]:
        """
        地理编码：通过地址获取经纬度（百度地理编码）

        Args:
            address: 详细地址

        Returns:
            包含经纬度和地址信息的字典
        """
        params = {
            "address": address,
            "output": "json",
            "ak": self.ak,
        }
        try:
            response = requests.get(self.geocode_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == 0:
                result = data.get("result", {})
                location = result.get("location", {})
                if location:
                    return {
                        "name": address,
                        "lng": location.get("lng"),
                        "lat": location.get("lat"),
                        "address": result.get("formatted_address"),
                        "province": result.get("addressComponent", {}).get("province"),
                        "city": result.get("addressComponent", {}).get("city"),
                        "district": result.get("addressComponent", {}).get("district"),
                    }
            else:
                print(f"百度地理编码失败: {data.get('message') or '未知错误'}")
        except requests.RequestException as e:
            print(f"请求错误: {e}")
        return None

    def get_location_info(self, location_name: str, city: str = None) -> Optional[Dict]:
        """
        获取地点信息，包含构建百度地图URL所需的参数
        """
        poi = self.search_poi(location_name, city)
        if poi:
            # 百度返回的坐标字段通常为 'location': {'lat': ..., 'lng': ...}
            loc = poi.get("location") or {}
            lat = loc.get("lat")
            lng = loc.get("lng")
            if lat is not None and lng is not None:
                return {
                    "name": poi.get("name", location_name),
                    "lnglat": f"{lng},{lat}",
                    "address": poi.get("address", ""),
                    "city": poi.get("city", city or ""),
                }

        # 回退到地理编码
        geo = self.geocode(location_name)
        if geo and geo.get("lng") is not None and geo.get("lat") is not None:
            return {
                "name": location_name,
                "lnglat": f"{geo['lng']},{geo['lat']}",
                "address": geo.get("address", ""),
                "city": geo.get("city", city or ""),
            }
        return None


def build_baidu_direction_url_from_names(ak: str, from_name: str, to_name: str,
                                         from_city: str = None, to_city: str = None,
                                         transport_mode: str = None) -> Optional[str]:
    """
    通过起点终点名称构建百度地图路线规划URL

    Args:
        ak: 百度地图服务AK
        from_name: 起点名称
        to_name: 终点名称
        from_city: 起点城市（可选）
        to_city: 终点城市（可选）
        transport_mode: 交通方式（driving/public_transit/walking），默认为driving

    Returns:
        完整的百度地图路线规划URL
    """
    service = BaiduLocationService(ak)
    mode = transport_mode or "driving"

    # 起点
    if from_name in ["当前位置", "我的位置", "这里", ""]:
        # 百度地图网页端不支持基于IP的“当前位置”坐标注入，这里将起点名称设置为“当前位置”以提示用户
        # 仍尝试从城市检索该关键词，否则作为名称传递
        from_info = service.get_location_info("当前位置", from_city) or {"name": "当前位置", "lnglat": ""}
    else:
        from_info = service.get_location_info(from_name, from_city)
    if not from_info:
        print(f"无法找到起点: {from_name}")
        return None

    # 终点
    to_info = service.get_location_info(to_name, to_city)
    if not to_info:
        print(f"无法找到终点: {to_name}")
        return None

    # 构建URL参数（百度地图Web方向页）
    base_url = "https://map.baidu.com/direction"
    params = {
        "mode": mode,
        "origin": from_info.get("name", from_name),
        "destination": to_info.get("name", to_name),
    }

    # 注入经纬度（如果可用），字段顺序：lat,lng
    if from_info.get("lnglat"):
        lng, lat = from_info["lnglat"].split(",")
        params["origin_latlng"] = f"{lat},{lng}"
    if to_info.get("lnglat"):
        lng, lat = to_info["lnglat"].split(",")
        params["destination_latlng"] = f"{lat},{lng}"

    query = urlencode(params, quote_via=quote)
    return f"{base_url}?{query}"

