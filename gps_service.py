"""
GPS定位服务模块
提供设备GPS位置获取功能
"""
import logging
from typing import Optional, Dict, Tuple
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPSService:
    """GPS定位服务类"""
    
    def __init__(self):
        self.system = platform.system()
        self.last_position = None
        logger.info(f"GPS服务初始化，系统: {self.system}")
    
    def check_gps_available(self) -> bool:
        """
        检查GPS是否可用
        
        Returns:
            bool: GPS是否可用
        """
        try:
            # 尝试导入QtPositioning模块
            from PySide6.QtPositioning import QGeoPositionInfoSource
            
            # 创建位置信息源
            source = QGeoPositionInfoSource.createDefaultSource(None)
            
            if source is None:
                logger.warning("无法创建GPS位置信息源")
                return False
            
            # 检查是否有可用的定位方法
            available = source.error() == QGeoPositionInfoSource.Error.NoError
            logger.info(f"GPS可用性检查结果: {available}")
            return available
            
        except ImportError:
            logger.warning("PySide6.QtPositioning模块不可用，GPS功能受限")
            return False
        except Exception as e:
            logger.error(f"检查GPS可用性时出错: {e}")
            return False
    
    def get_current_gps_location(self) -> Optional[Tuple[float, float]]:
        """
        获取当前GPS位置（经纬度）
        
        Returns:
            Optional[Tuple[float, float]]: (经度, 纬度) 或 None
        """
        try:
            from PySide6.QtPositioning import QGeoPositionInfoSource
            from PySide6.QtCore import QEventLoop, QTimer
            
            # 创建位置信息源
            source = QGeoPositionInfoSource.createDefaultSource(None)
            
            if source is None:
                logger.warning("无法创建GPS位置信息源")
                return None
            
            # 设置更新间隔
            source.setUpdateInterval(5000)  # 5秒
            
            # 用于存储位置信息的容器
            position_data = {'position': None, 'received': False}
            
            def on_position_updated(position):
                """位置更新回调"""
                if position.isValid():
                    coord = position.coordinate()
                    if coord.isValid():
                        position_data['position'] = (coord.longitude(), coord.latitude())
                        position_data['received'] = True
                        logger.info(f"GPS位置获取成功: {coord.longitude()}, {coord.latitude()}")
            
            def on_error(error):
                """错误回调"""
                logger.error(f"GPS定位错误: {error}")
                position_data['received'] = True  # 标记为已完成，即使是错误
            
            # 连接信号
            source.positionUpdated.connect(on_position_updated)
            source.errorOccurred.connect(on_error)
            
            # 请求单次更新
            source.requestUpdate(10000)  # 10秒超时
            
            # 等待位置更新或超时
            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(10000)  # 10秒超时
            
            # 当收到位置或发生错误时退出循环
            def check_and_quit():
                if position_data['received']:
                    loop.quit()
            
            timer2 = QTimer()
            timer2.timeout.connect(check_and_quit)
            timer2.start(100)  # 每100ms检查一次
            
            loop.exec()
            timer.stop()
            timer2.stop()
            
            if position_data['position']:
                self.last_position = position_data['position']
                return position_data['position']
            else:
                logger.warning("GPS定位超时或失败")
                return None
                
        except ImportError:
            logger.warning("PySide6.QtPositioning模块不可用")
            return None
        except Exception as e:
            logger.error(f"获取GPS位置时出错: {e}")
            return None
    
    def get_location_info(self) -> Optional[Dict]:
        """
        获取当前位置信息，返回标准格式
        
        Returns:
            Optional[Dict]: 位置信息字典，与地图服务格式兼容
        """
        coords = self.get_current_gps_location()
        
        if coords:
            lng, lat = coords
            return {
                'id': '',
                'name': 'GPS定位',
                'lnglat': f"{lng},{lat}",
                'modxy': f"{lng},{lat}",
                'poitype': '',
                'adcode': '',
                'address': 'GPS定位',
                'citycode': '',
                'cityname': '',
                'district': ''
            }
        return None
    
    def get_last_known_position(self) -> Optional[Tuple[float, float]]:
        """
        获取上次已知的位置
        
        Returns:
            Optional[Tuple[float, float]]: (经度, 纬度) 或 None
        """
        return self.last_position


if __name__ == "__main__":
    # 测试GPS服务
    gps = GPSService()
    
    print("检查GPS可用性...")
    if gps.check_gps_available():
        print("✅ GPS可用")
        
        print("\n获取GPS位置...")
        location = gps.get_current_gps_location()
        if location:
            print(f"✅ GPS位置: 经度={location[0]}, 纬度={location[1]}")
        else:
            print("❌ 无法获取GPS位置")
    else:
        print("❌ GPS不可用，请检查设备设置")
