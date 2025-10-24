import requests
from typing import Dict, Optional
from urllib.parse import urlencode, quote
from enum import Enum


class TransportMode(Enum):
    DRIVING = "car"
    TAXI = "car"
    PUBLIC_TRANSIT = "bus"
    CARPOOLING = "car"
    CYCLING = "bike"
    WALKING = "walk"
    TRAIN = "car"
    AIRPLANE = "car"
    MOTORCYCLE = "car"


class AmapLocationService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3"
    
    def search_poi(self, keywords: str, city: str = None) -> Optional[Dict]:
        """
        通过关键词搜索POI信息
        
        Args:
            keywords: 搜索关键词（地点名称）
            city: 搜索城市（可选，建议填写提高准确性）
        
        Returns:
            包含POI详细信息的字典，包括经纬度、POI类型编码、行政区划代码等
        """
        url = f"{self.base_url}/place/text"
        
        params = {
            'key': self.api_key,
            'keywords': keywords,
            'output': 'json',
            'page': 1,
            'offset': 20
        }
        
        if city:
            params['city'] = city
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('pois'):
                return data['pois'][0]  # 返回第一个最匹配的结果
            else:
                print(f"搜索失败: {data.get('info', '未知错误')}")
                return None
                
        except requests.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def geocode(self, address: str) -> Optional[Dict]:
        """
        地理编码：通过地址获取经纬度
        
        Args:
            address: 详细地址
            
        Returns:
            包含经纬度和地址信息的字典
        """
        url = f"{self.base_url}/geocode/geo"
        
        params = {
            'key': self.api_key,
            'address': address,
            'output': 'json'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('geocodes'):
                return data['geocodes'][0]
            else:
                print(f"地理编码失败: {data.get('info', '未知错误')}")
                return None
                
        except requests.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def get_location_info(self, location_name: str, city: str = None) -> Optional[Dict]:
        """
        获取地点的完整信息，包括构建高德地图URL所需的所有参数
        
        Args:
            location_name: 地点名称
            city: 城市名称（可选）
            
        Returns:
            包含所有URL构建所需信息的字典
        """
        # 首先尝试POI搜索
        poi_result = self.search_poi(location_name, city)
        
        if poi_result:
            location = poi_result.get('location', '').split(',')
            if len(location) == 2:
                lng, lat = location[0], location[1]
                
                return {
                    'id': poi_result.get('id', ''),
                    'name': poi_result.get('name', location_name),
                    'lnglat': f"{lng},{lat}",
                    'modxy': f"{lng},{lat}",  # 通常与lnglat相同，或略有偏移
                    'poitype': poi_result.get('typecode', ''),
                    'adcode': poi_result.get('adcode', ''),
                    'address': poi_result.get('address', ''),
                    'citycode': poi_result.get('citycode', ''),
                    'cityname': poi_result.get('cityname', ''),
                    'district': poi_result.get('adname', '')
                }
        
        # 如果POI搜索失败，尝试地理编码
        geocode_result = self.geocode(location_name)
        if geocode_result:
            location = geocode_result.get('location', '').split(',')
            if len(location) == 2:
                lng, lat = location[0], location[1]
                
                return {
                    'id': '',
                    'name': location_name,
                    'lnglat': f"{lng},{lat}",
                    'modxy': f"{lng},{lat}",
                    'poitype': '',
                    'adcode': geocode_result.get('adcode', ''),
                    'address': geocode_result.get('formatted_address', ''),
                    'citycode': geocode_result.get('citycode', ''),
                    'cityname': geocode_result.get('city', ''),
                    'district': geocode_result.get('district', '')
                }
        
        return None


def build_amap_direction_url_from_names(api_key: str, from_name: str, to_name: str, 
                                       from_city: str = None, to_city: str = None,
                                       route_type: str = 'car', policy: int = 1,
                                       transport_mode: str = None) -> Optional[str]:
    """
    通过起点终点名称构建高德地图路线规划URL
    
    Args:
        api_key: 高德地图API密钥
        from_name: 起点名称
        to_name: 终点名称
        from_city: 起点城市（可选）
        to_city: 终点城市（可选）
        route_type: 路线类型（保留兼容性）
        policy: 路线策略
        transport_mode: 交通方式（driving/taxi/public_transit/carpooling/cycling/walking/train/airplane/motorcycle）
        
    Returns:
        完整的高德地图路线规划URL
    """
    service = AmapLocationService(api_key)
    
    if transport_mode:
        try:
            mode_enum = TransportMode[transport_mode.upper()]
            route_type = mode_enum.value
        except KeyError:
            route_type = TransportMode.DRIVING.value
    
    # 获取起点信息
    from_info = service.get_location_info(from_name, from_city)
    if not from_info:
        print(f"无法找到起点: {from_name}")
        return None
    
    # 获取终点信息
    to_info = service.get_location_info(to_name, to_city)
    if not to_info:
        print(f"无法找到终点: {to_name}")
        return None
    
    # 构建URL参数
    base_url = "https://www.amap.com/dir"
    params = {}
    
    # 起点参数
    for key, value in from_info.items():
        if key in ['id', 'name', 'lnglat', 'modxy', 'poitype', 'adcode']:
            params[f'from[{key}]'] = value
    
    # 终点参数
    for key, value in to_info.items():
        if key in ['id', 'name', 'lnglat', 'modxy', 'poitype', 'adcode']:
            params[f'to[{key}]'] = value
    
    # 路线参数
    params['type'] = route_type
    params['policy'] = policy
    
    # 构建URL
    query_string = urlencode(params, quote_via=quote)
    return f"{base_url}?{query_string}"


if __name__ == "__main__":
    # 需要替换为你的高德地图API密钥
    API_KEY = "3b16354b4a04610cf4873088846dfcb6"
    
    # 示例：从上海新天地到中友嘉园
    url = build_amap_direction_url_from_names(
        api_key=API_KEY,
        from_name="上海新天地",
        to_name="中友嘉园", 
        from_city="上海",
        to_city="上海"
    )
    
    if url:
        print("生成的高德地图URL:")
        print(url)
    else:
        print("URL生成失败")
        
    # 也可以单独获取地点信息
    service = AmapLocationService(API_KEY)
    location_info = service.get_location_info("天安门", "北京")
    if location_info:
        print("\n地点信息:")
        for key, value in location_info.items():
            print(f"{key}: {value}")