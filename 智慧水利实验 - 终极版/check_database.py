import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta
import sys
import io

# 设置标准输出编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class DataViewer:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Eric0314',
            'database': 'hydro_monitoring'
        }

    def view_latest_data(self, limit=10):
        """查看最新数据"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            query = """
            SELECT timestamp, sensor_id, value, metric_type
            FROM hydro_data
            ORDER BY timestamp DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            print(f"\n最新{limit}条数据：")
            print("时间\t\t\t传感器ID\t数值\t\t类型")
            print("-" * 70)
            for row in results:
                print(f"{row[0]}\t{row[1]}\t{row[2]:.2f}\t\t{row[3]}")
                
        except Error as error:
            print(f"查询数据时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def view_data_by_type(self, metric_type, hours=24):
        """查看指定类型的数据"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            query = """
            SELECT timestamp, value
            FROM hydro_data
            WHERE metric_type = %s
            AND timestamp >= NOW() - INTERVAL %s HOUR
            ORDER BY timestamp
            """
            cursor.execute(query, (metric_type, hours))
            results = cursor.fetchall()
            
            print(f"\n最近{hours}小时的{metric_type}数据：")
            print("时间\t\t\t数值")
            print("-" * 40)
            for row in results:
                print(f"{row[0]}\t{row[1]:.2f}")
                
        except Error as error:
            print(f"查询数据时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_statistics(self):
        """获取统计信息"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            query = """
            SELECT 
                metric_type,
                COUNT(*) as count,
                MIN(value) as min_value,
                MAX(value) as max_value,
                AVG(value) as avg_value,
                STDDEV(value) as std_value  # 添加标准差
            FROM hydro_data
            GROUP BY metric_type
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("\n数据统计信息：")
            print("类型\t\t数量\t最小值\t最大值\t平均值\t标准差")
            print("-" * 60)
            for row in results:
                print(f"{row[0]}\t{row[1]}\t{row[2]:.3f}\t{row[3]:.3f}\t{row[4]:.3f}\t{row[5]:.3f}")
                
        except Error as error:
            print(f"查询统计信息时出错: {error}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

if __name__ == "__main__":
    viewer = DataViewer()
    
    # 查看最新数据
    viewer.view_latest_data(10)
    
    # 查看各类型数据
    print("\n查看各类型数据：")
    for metric_type in ['水位', '流量', '降水量', '蒸发量']:
        viewer.view_data_by_type(metric_type, 24)
    
    # 查看统计信息
    viewer.get_statistics()