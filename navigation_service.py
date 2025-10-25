import os
import webbrowser
from amap_service import build_amap_direction_url_from_names
from baidu_service import build_baidu_direction_url_from_names


class NavigationService:
    def __init__(self, api_key: str = None, provider: str = None):
        # 读取环境变量中的API Key和地图提供方
        self.amap_api_key = api_key or os.getenv("AMAP_API_KEY", "3b16354b4a04610cf4873088846dfcb6")
        self.baidu_api_key = os.getenv("BAIDU_MAP_AK", "vE2HgtbueyifzmUlFy09ev6lzktj2ifF")
        self.provider = (provider or os.getenv("MAP_PROVIDER", "amap")).lower()
    
    def navigate(self, start_point: str, end_point: str, start_city: str = None, end_city: str = None, transport_mode: str = None):
        """
        根据起点和终点打开高德地图导航链接
        
        Args:
            start_point: 起点名称
            end_point: 终点名称
            start_city: 起点城市（可选）
            end_city: 终点城市（可选）
            transport_mode: 交通方式（可选）
        
        Returns:
            bool: 是否成功打开链接
        """
        if self.provider == "baidu":

            url = build_baidu_direction_url_from_names(
                api_key=self.baidu_api_key,
                from_name=start_point,
                to_name=end_point,
                from_city=start_city,
                to_city=end_city,
                transport_mode=transport_mode,
            )
        elif self.provider == "amap":
            url = build_amap_direction_url_from_names(
                api_key=self.amap_api_key,
                from_name=start_point,
                to_name=end_point,
                from_city=start_city,
                to_city=end_city,
                transport_mode=transport_mode,
            )
        
        if url:
            try:
                webbrowser.open(url)
                print(f"已打开导航: {start_point} → {end_point}")
                return True
            except Exception as e:
                print(f"打开浏览器失败: {e}")
                return False
        else:
            print("生成导航链接失败")
            return False


if __name__ == "__main__":
    nav_service = NavigationService(provider=os.getenv("MAP_PROVIDER", "amap"))
    nav_service.navigate("上海新天地", "中友嘉园", "上海", "上海")
