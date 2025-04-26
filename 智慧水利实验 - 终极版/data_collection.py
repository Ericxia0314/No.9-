import requests
import datetime
import math
import numpy as np
import mysql.connector
from mysql.connector import Error
import sys
import io

# 设置标准输出编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class HydroModel:
    def __init__(self):
        # 调整水文模型参数
        self.params = {
            'infiltration_rate': 0.2,     
            'runoff_coefficient': 0.15,    # 进一步减小径流系数，使降水对水位影响更平缓
            'base_flow': 50.0,           
            'base_level': 2.4,            # 调整基础水位
            'response_time': 6,           # 增加响应时间，使水位变化更平滑
        }
        
        # 减小随机波动范围，使数据更平滑
        self.fluctuation = {
            'water_level': 0.02,    # 大幅减小水位波动范围
            'flow_rate': 0.5,       # 减小流量波动范围
            'rainfall': 0.2,        # 保持降水波动范围
            'evaporation': 0.05     # 保持蒸发波动范围
        }
        
        # 状态变量
        self.prev_rainfall = 0
        self.prev_water_level = self.params['base_level']
        self.prev_flow_rate = self.params['base_flow']
        
        # 移除明显的周期性变化参数，改为更自然的随机波动
        self.daily_cycle_amplitude = 0.005  # 大幅减小日周期振幅
        self.weekly_cycle_amplitude = 0.01  # 大幅减小周周期振幅
        
        # 添加历史数据缓冲区，用于平滑处理，增加缓冲区大小
        self.water_level_history = [self.params['base_level']] * 10  # 增加历史数据点数量
        self.flow_rate_history = [self.params['base_flow']] * 10
        
        # 添加长期趋势变量
        self.trend_factor = 0.0001
        self.trend_direction = 1  # 1表示上升，-1表示下降
        self.trend_change_counter = 0
        self.trend_change_threshold = 50  # 趋势变化阈值

    def _calculate_evaporation(self, temperature, humidity):
        """计算蒸发量"""
        # 简化的蒸发量计算公式
        saturation_vapor = 6.112 * math.exp((17.67 * temperature) / (temperature + 243.5))
        actual_vapor = saturation_vapor * (humidity / 100)
        evaporation = max(0, (saturation_vapor - actual_vapor) * 0.0018)
        return evaporation

    def simulate_data(self, timestamp):
        """模拟生成数据"""
        hour = timestamp.hour
        minute = timestamp.minute
        day = timestamp.day
        time_factor = hour + minute / 60  # 时间因子
        day_factor = day % 7  # 周因子
        
        # 生成降水量（模拟早晨和傍晚降雨的情况）- 使用更平滑的曲线
        rainfall = 0.1 + 1.5 * math.exp(-((time_factor - 6) ** 2) / 15) + \
                  2 * math.exp(-((time_factor - 18) ** 2) / 15)
        # 减小随机波动
        rainfall = max(0, rainfall + np.random.normal(0, self.fluctuation['rainfall'] * 0.5))
        
        # 生成温度（日变化）
        temperature = 20 + 8 * math.sin(math.pi * (time_factor - 6) / 12)
        
        # 生成湿度（与温度相关）
        humidity = 80 - 30 * math.sin(math.pi * (time_factor - 6) / 12)
        humidity = min(100, max(40, humidity + np.random.normal(0, 3)))
        
        # 计算水文参数
        water_level = self.calculate_water_level(rainfall, temperature, timestamp)
        flow_rate = self.calculate_flow_rate(rainfall, water_level)
        evaporation = self._calculate_evaporation(temperature, humidity)
        
        return {
            'rainfall': rainfall,
            'water_level': water_level,
            'flow_rate': flow_rate,
            'evaporation': evaporation
        }

    def calculate_water_level(self, rainfall, temp, timestamp):
        """计算水位变化，增加平滑处理和自然随机性"""
        # 考虑降雨和温度影响
        infiltration = rainfall * self.params['infiltration_rate'] * (1 + (temp - 20) * 0.01)
        effective_rain = rainfall * (1 - self.params['infiltration_rate'])
        
        # 水位变化计算 - 减小降雨对水位的即时影响
        level_change = (effective_rain / 300) * self.params['runoff_coefficient']
        
        # 添加更自然的随机波动，而不是强周期性变化
        hour = timestamp.hour
        minute = timestamp.minute
        
        # 大幅减弱周期性变化，增加随机性
        daily_cycle = self.daily_cycle_amplitude * math.sin(2 * math.pi * (hour + minute/60) / 24)
        
        # 添加长期趋势变化
        self.trend_change_counter += 1
        if self.trend_change_counter > self.trend_change_threshold:
            # 随机改变趋势方向
            if np.random.random() > 0.7:  # 30%的概率改变趋势
                self.trend_direction *= -1
                self.trend_change_counter = 0
                self.trend_change_threshold = np.random.randint(40, 100)  # 随机设置下一次变化的阈值
        
        trend_change = self.trend_factor * self.trend_direction
        
        # 添加自然随机波动，使用更小的随机因子
        random_fluctuation = np.random.normal(0, self.fluctuation['water_level'] / 10)
        
        # 计算新水位 - 考虑历史水位的平均值，实现平滑过渡
        raw_new_level = self.prev_water_level + level_change + daily_cycle + trend_change + random_fluctuation
        
        # 考虑退水过程 - 更平缓
        if rainfall < self.prev_rainfall:
            recession = 1 - 0.01 * self.params['response_time']  # 进一步减小退水速率
            raw_new_level = self.prev_water_level * recession + self.params['base_level'] * (1 - recession)
        
        # 使用移动平均平滑水位变化，增加平滑效果
        self.water_level_history.append(raw_new_level)
        self.water_level_history.pop(0)
        smoothed_level = sum(self.water_level_history) / len(self.water_level_history)
        
        # 确保水位有合理的变化范围
        min_level = self.params['base_level'] - 0.1
        max_level = self.params['base_level'] + 0.15
        new_level = max(min_level, min(max_level, smoothed_level))
        
        # 限制与前一个水位的变化幅度
        max_change = 0.005  # 进一步限制每次最大变化幅度
        if abs(new_level - self.prev_water_level) > max_change:
            if new_level > self.prev_water_level:
                new_level = self.prev_water_level + max_change
            else:
                new_level = self.prev_water_level - max_change
        
        # 更新状态
        self.prev_water_level = new_level
        self.prev_rainfall = rainfall
        
        return self.prev_water_level

    def calculate_flow_rate(self, rainfall, water_level):
        """计算流量，增加平滑处理"""
        # 基于水位和降雨量计算流量
        level_diff = water_level - self.params['base_level']
        flow_change = level_diff * 15 + rainfall * self.params['runoff_coefficient'] * 0.8  # 减小水位对流量的影响
        
        # 添加极小的随机波动
        random_fluctuation = np.random.normal(0, self.fluctuation['flow_rate'] / 15)
        
        # 计算原始新流量
        raw_new_flow = self.params['base_flow'] + flow_change + random_fluctuation
        
        # 使用移动平均平滑流量变化
        self.flow_rate_history.append(raw_new_flow)
        self.flow_rate_history.pop(0)
        smoothed_flow = sum(self.flow_rate_history) / len(self.flow_rate_history)
        
        # 限制流量变化范围
        new_flow = max(self.params['base_flow'] - 1.0, min(self.params['base_flow'] + 1.5, smoothed_flow))
        
        # 限制与前一个流量的变化幅度
        max_change = 0.1  # 限制每次最大变化幅度
        if abs(new_flow - self.prev_flow_rate) > max_change:
            if new_flow > self.prev_flow_rate:
                new_flow = self.prev_flow_rate + max_change
            else:
                new_flow = self.prev_flow_rate - max_change
        
        self.prev_flow_rate = new_flow
        return self.prev_flow_rate

class DatabaseManager:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Eric0314',
            'database': 'hydro_monitoring'
        }

    def create_database(self):
        """创建数据库"""
        try:
            connection = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS hydro_monitoring")
            print("数据库创建成功")
        except Error as error:
            print(f"创建数据库时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def create_tables(self):
        """创建数据表"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS hydro_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                sensor_id VARCHAR(10),
                value FLOAT,
                metric_type VARCHAR(20)
            )
            """
            cursor.execute(create_table_query)
            print("数据表创建成功")
        except Error as error:
            print(f"创建数据表时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def save_data(self, data):
        """保存数据到数据库"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            metrics = {
                'water_level': '水位',
                'flow_rate': '流量',
                'rainfall': '降水量',
                'evaporation': '蒸发量'
            }
            
            for eng_name, cn_name in metrics.items():
                if eng_name in data:
                    insert_query = """
                    INSERT INTO hydro_data (timestamp, sensor_id, value, metric_type)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (
                        data['timestamp'],
                        data['sensor_id'],
                        data[eng_name],
                        cn_name
                    ))
            
            connection.commit()
            print("数据保存成功")
            
        except Error as error:
            print(f"保存数据时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def cleanup_excess_data(self, keep_records=1000):
        """清理多余的数据"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            delete_query = """
            DELETE FROM hydro_data 
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id FROM hydro_data 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                ) AS temp
            )
            """
            cursor.execute(delete_query, (keep_records,))
            connection.commit()
            print(f"已清理数据，保留最新的{keep_records}条记录")
        except Error as error:
            print(f"清理数据时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

class SensorDataCollector:
    def __init__(self, sensor_id):
        self.sensor_id = sensor_id
        self.api_key = "e1a1fa4981304c11ba7ec460bc0a79b9"
        self.base_url = "https://kx7p3yfd47.re.qweatherapi.com/v7"
        self.hydro_model = HydroModel()
        self.db_manager = DatabaseManager()
        
    def initialize_database(self):
        """初始化数据库"""
        self.db_manager.create_database()
        self.db_manager.create_tables()

    def collect_and_save_data(self):
        """收集并保存数据"""
        data = self.collect_data()
        if data:
            self.db_manager.save_data(data)
            return data
        return None

    def collect_data(self):
        try:
            # 获取气象数据
            params = {
                "location": "101210101",  # 杭州
                "key": self.api_key,
                "lang": "zh",
                "unit": "m"
            }
            
            response = requests.get(
                f"{self.base_url}/weather/now",
                params=params
            )
            
            if response.status_code == 200:
                weather_data = response.json()
                now = weather_data['now']
                
                # 获取气象参数
                rainfall = float(now['precip'])  # 降水量(mm)
                temperature = float(now['temp'])  # 温度(℃)
                humidity = float(now['humidity']) # 湿度(%)
                
                # 使用水文模型计算水文参数
                water_level = self.hydro_model.calculate_water_level(rainfall, temperature)
                flow_rate = self.hydro_model.calculate_flow_rate(rainfall, water_level)
                
                # 计算蒸发量（基于温度和湿度）
                evaporation = self._calculate_evaporation(temperature, humidity)
                
                return {
                    'sensor_id': self.sensor_id,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'water_level': water_level,
                    'flow_rate': flow_rate,
                    'rainfall': rainfall,
                    'evaporation': evaporation
                }
            else:
                raise Exception(f"API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"数据采集错误: {str(e)}")
            return None
            
class ExternalAPIClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        
    def fetch_data(self, endpoint, params=None):
        try:
            response = requests.get(
                self.base_url + endpoint,
                params=params,
                timeout=10
            )
            
            # 设置响应编码
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API请求失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {str(e)}")
            return None
        except Exception as e:
            print(f"其他错误: {str(e)}")
            return None


if __name__ == "__main__":
    collector = SensorDataCollector("SENSOR_001")
    collector.initialize_database()
    
    # 计算24小时内的时间点
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(hours=24)
    time_interval = datetime.timedelta(minutes=5)
    current_time = start_time
    
    print("开始生成24小时模拟数据...")
    while current_time <= end_time:
        # 使用模拟数据替代实时API数据
        simulated_data = collector.hydro_model.simulate_data(current_time)
        data = {
            'sensor_id': collector.sensor_id,
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'water_level': simulated_data['water_level'],
            'flow_rate': simulated_data['flow_rate'],
            'rainfall': simulated_data['rainfall'],
            'evaporation': simulated_data['evaporation']
        }
        
        collector.db_manager.save_data(data)
        print(f"生成时间点: {data['timestamp']} 成功")
        current_time += time_interval
    
    print("24小时数据生成完成")
    collector.db_manager.cleanup_excess_data(1000)