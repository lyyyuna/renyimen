import json
import os
import webbrowser
from amap_service import build_amap_direction_url_from_names
from baidu_service import build_baidu_direction_url_from_names


class NavigationService:
    def __init__(self, api_key: str = "3b16354b4a04610cf4873088846dfcb6", provider: str = None):
        self.api_key = api_key
        self.provider = provider or self._load_provider()

    def _load_provider(self) -> str:
        cfg_path = os.path.join(os.path.dirname(__file__), "provider_config.json")
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    prov = str(data.get("provider", "amap")).lower()
                    return prov if prov in ("amap", "baidu") else "amap"
        except Exception:
            pass
        return "amap"
    
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
        if (self.provider or "amap") == "amap":
            url = build_amap_direction_url_from_names(
                api_key=self.api_key,
                from_name=start_point,
                to_name=end_point,
                from_city=start_city,
                to_city=end_city,
                transport_mode=transport_mode
            )
        else:
            url = build_baidu_direction_url_from_names(
                from_name=start_point,
                to_name=end_point,
                from_city=start_city,
                to_city=end_city,
                transport_mode=transport_mode
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
    nav_service = NavigationService()
    nav_service.navigate("上海新天地", "中友嘉园", "上海", "上海")
