#- 用户名：admin
#- 密码：admin123
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from functools import wraps  # 添加这行导入
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import logging
from data_collection import SensorDataCollector
# 在文件顶部添加导入
from visualization_functions import (
    create_heatmap_visualization,
    create_3d_surface_visualization,
    create_radar_visualization,
    create_map_visualization,
    create_animation_visualization
)
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('hydro_web.log', 'w', 'utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key_here'  # 添加密钥用于session加密
collector = SensorDataCollector("SENSOR_001")

# 添加登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 添加登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Eric0314",
                database="hydro_monitoring"
            )
            cursor = connection.cursor()
            
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()
            
            if user:
                session['username'] = username
                session['role'] = user[3]
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="用户名或密码错误")
                
        except Error as error:
            logging.error(f"数据库错误: {error}")
            return render_template('login.html', error="系统错误")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return render_template('login.html')

# 添加注销路由
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def get_latest_data(hours=24):
    """从数据库获取最新数据"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Eric0314",
            database="hydro_monitoring"
        )
        cursor = connection.cursor()
        
        # 查询语句
        query = """
        SELECT timestamp, metric_type, value 
        FROM hydro_data 
        WHERE timestamp >= NOW() - INTERVAL %s HOUR
        ORDER BY timestamp ASC, metric_type
        """
        cursor.execute(query, (hours,))
        results = cursor.fetchall()
        
        # 使用字典存储每个时间点的数据
        data_points = {}
        for row in results:
            timestamp, metric_type, value = row
            if timestamp not in data_points:
                data_points[timestamp] = {'timestamp': timestamp}
            data_points[timestamp][metric_type] = value

        # 整理数据，确保每个时间点都有完整的数据
        data = {
            'timestamps': [],
            'water_levels': [],
            'flow_rates': [],
            'rainfall': [],
            'evaporation': []
        }
        
        for timestamp in sorted(data_points.keys()):
            point = data_points[timestamp]
            data['timestamps'].append(point['timestamp'])
            data['water_levels'].append(point.get('水位', None))
            data['flow_rates'].append(point.get('流量', None))
            data['rainfall'].append(point.get('降水量', 0))
            data['evaporation'].append(point.get('蒸发量', 0))
        
        # 移除插值处理部分，直接返回原始数据
        return data
        
    except Error as error:
        logging.error(f"数据库查询错误: {error}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def create_visualization(data, page=1):
    """创建分页可视化图表"""
    if page == 1:
        # 第一页：水位和流量
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('水位变化趋势', '流量实时监测'),
            vertical_spacing=0.2,
            specs=[[{"type": "scatter"}], [{"type": "scatter"}]]
        )
        
        # 计算水位的最小值和最大值
        min_water = min(data['water_levels']) if data['water_levels'] else 0
        max_water = max(data['water_levels']) if data['water_levels'] else 1
        
        # 调整y轴范围，扩大范围使波动看起来更小
        y_min_water = 2.0  # 设置更低的下限值
        y_max_water = 2.8  # 设置更高的上限值
        
        # 水位数据 - 使用折线图，增加平滑度
        fig.add_trace(
            go.Scatter(
                x=data['timestamps'], 
                y=data['water_levels'],
                name='水位',
                fill='tozeroy',
                fillcolor='rgba(0, 128, 255, 0.2)',
                line=dict(color='rgb(0, 128, 255)', width=2, shape='spline', smoothing=0.3),  # 使用平滑曲线
                hovertemplate='时间: %{x}<br>水位: %{y:.2f}m<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 设置水位y轴范围
        fig.update_yaxes(range=[y_min_water, y_max_water], row=1, col=1)
        
        # 计算流量的最小值和最大值
        min_flow = min(data['flow_rates']) if data['flow_rates'] else 0
        max_flow = max(data['flow_rates']) if data['flow_rates'] else 1
        
        # 调整流量y轴范围，同样扩大范围
        y_min_flow = 45.0  # 设置更低的下限值
        y_max_flow = 55.0  # 设置更高的上限值
        
        # 流量数据 - 使用折线图，增加平滑度
        fig.add_trace(
            go.Scatter(
                x=data['timestamps'],
                y=data['flow_rates'],
                name='流量',
                line=dict(color='rgb(255, 69, 0)', width=2, shape='spline', smoothing=0.3),  # 使用平滑曲线
                hovertemplate='时间: %{x}<br>流量: %{y:.2f}m³/s<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 设置流量y轴范围
        fig.update_yaxes(range=[y_min_flow, y_max_flow], row=2, col=1)
        
    elif page == 2:
        # 第二页：降水量和蒸发量
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('降水量统计', '蒸发量分析'),
            vertical_spacing=0.2,
            specs=[[{"type": "bar"}], [{"type": "bar"}]]
        )
        
        # 降水量
        fig.add_trace(
            go.Bar(
                x=data['timestamps'],
                y=data['rainfall'],
                name='降水量',
                marker_color='rgb(30, 144, 255)',
                hovertemplate='时间: %{x}<br>降水量: %{y:.2f}mm<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 蒸发量
        fig.add_trace(
            go.Bar(
                x=data['timestamps'],
                y=data['evaporation'],
                name='蒸发量',
                marker=dict(
                    color=data['evaporation'],
                    colorscale='Reds',
                    showscale=True
                ),
                hovertemplate='时间: %{x}<br>蒸发量: %{y:.2f}mm<extra></extra>'
            ),
            row=2, col=1
        )
        
    else:
        # 第三页：预警状态
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('当前水位状态', '预警监测'),
            specs=[[{"type": "indicator"}, {"type": "indicator"}]]
        )
        
        latest_water = data['water_levels'][-1] if data['water_levels'] else 0
        warning_level = 0.8
        warning_status = "正常" if latest_water < warning_level else "预警"
        
        # 计算水位的最小值和最大值
        min_water = min(data['water_levels']) if data['water_levels'] else 0
        max_water = max(data['water_levels']) if data['water_levels'] else 1
        # 设置仪表盘范围，使变化更明显
        gauge_max = max(max_water * 1.1, warning_level * 1.2)
        
        # 添加仪表盘
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=latest_water,
                title={'text': "当前水位(m)"},
                gauge={'axis': {'range': [min_water * 0.9, gauge_max]},
                      'bar': {'color': "rgb(0, 128, 255)"}},
            ),
            row=1, col=1
        )
        
        # 添加预警指示器
        fig.add_trace(
            go.Indicator(
                mode="number+delta+gauge",
                value=latest_water,
                delta={'reference': warning_level},
                title={'text': f"预警状态: {warning_status}"},
                gauge={
                    'axis': {'range': [0, warning_level * 1.5]},
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': warning_level
                    },
                    'steps': [
                        {'range': [0, warning_level], 'color': "lightgreen"},
                        {'range': [warning_level, warning_level * 1.5], 'color': "lightpink"}
                    ]
                }
            ),
            row=1, col=2
        )

    # 更新布局样式
    fig.update_layout(
        height=800,  # 调整图表高度
        showlegend=True,
        title_text=f"智慧水利监测系统数据可视化 - 第{page}页",
        title_x=0.5,
        title_font_size=24,
        plot_bgcolor='rgba(240,240,240,0.2)',
        paper_bgcolor='white',
        font=dict(size=12),
        hovermode='x unified',
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(t=100, l=50, r=50, b=50)
    )
    
    return fig

@app.route('/')
@login_required
def index():
    try:
        page = request.args.get('page', 1, type=int)
        if page not in [1, 2, 3]:
            page = 1
            
        plot_data = get_latest_data(24)
        if plot_data and plot_data['water_levels']:
            fig = create_visualization(plot_data, page)
            latest_data = {
                'water_level': plot_data['water_levels'][-1],
                'flow_rate': plot_data['flow_rates'][-1],
                'rainfall': plot_data['rainfall'][-1],
                'evaporation': plot_data['evaporation'][-1]
            }
            
            return render_template('hydro_index.html',
                                 plot_html=fig.to_html(full_html=False),
                                 current_data=latest_data,
                                 username=session['username'],
                                 current_page=page)
        else:
            return render_template('hydro_index.html', error="无数据")
    except Exception as e:
        logging.error(f"页面渲染错误: {str(e)}")
        return render_template('hydro_index.html', error="数据加载失败")

@app.route('/collect_data', methods=['POST'])
def collect_new_data():
    """手动收集新数据"""
    try:
        data = collector.collect_and_save_data()
        if data:
            return jsonify({'status': 'success', 'message': '数据收集成功'})
        return jsonify({'status': 'error', 'message': '数据收集失败'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/advanced_viz')
@login_required
def advanced_visualization():
    try:
        viz_type = request.args.get('type', 'heatmap')
        plot_data = get_latest_data(24)
        
        if plot_data and plot_data['water_levels']:
            if viz_type == 'heatmap':
                fig = create_heatmap_visualization(plot_data)
            elif viz_type == '3d':
                fig = create_3d_surface_visualization(plot_data)
            elif viz_type == 'radar':
                fig = create_radar_visualization(plot_data)
            elif viz_type == 'map':
                fig = create_map_visualization(plot_data)
            elif viz_type == 'animation':
                fig = create_animation_visualization(plot_data)
            else:
                fig = create_heatmap_visualization(plot_data)
                
            return render_template('advanced_viz.html',
                                 plot_html=fig.to_html(full_html=False),
                                 username=session['username'],
                                 viz_type=viz_type)
        else:
            return render_template('advanced_viz.html', error="无数据")
    except Exception as e:
        logging.error(f"高级可视化错误: {str(e)}")
        return render_template('advanced_viz.html', error="数据加载失败")

if __name__ == '__main__':
    from waitress import serve
    logging.info("服务器启动在 http://127.0.0.1:5000")
    serve(app, host='127.0.0.1', port=5000)

