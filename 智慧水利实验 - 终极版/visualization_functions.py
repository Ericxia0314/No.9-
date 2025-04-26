import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots

def create_heatmap_visualization(data):
    """替换热力图为相关性分析图"""
    import numpy as np
    
    # 计算各指标之间的相关性
    metrics = ['水位', '流量', '降水量', '蒸发量']
    correlation_matrix = np.ones((4, 4))  # 初始化相关矩阵
    
    # 提取有效数据并处理缺失值
    water_levels = np.array(data['water_levels'])
    flow_rates = np.array(data['flow_rates'])
    rainfall = np.array(data['rainfall'])
    evaporation = np.array(data['evaporation'])
    
    # 计算相关系数，增强健壮性
    def correlation(x, y):
        # 移除两个数组中任一为None的对应元素
        valid_indices = []
        for i in range(len(x)):
            if x[i] is not None and y[i] is not None:
                valid_indices.append(i)
        
        if len(valid_indices) < 2:  # 至少需要两个点才能计算相关性
            return 0
            
        x_valid = np.array([x[i] for i in valid_indices])
        y_valid = np.array([y[i] for i in valid_indices])
        
        if np.std(x_valid) == 0 or np.std(y_valid) == 0:
            return 0
            
        return np.corrcoef(x_valid, y_valid)[0, 1]
    
    # 填充相关矩阵
    correlation_matrix[0, 1] = correlation_matrix[1, 0] = correlation(water_levels, flow_rates)
    correlation_matrix[0, 2] = correlation_matrix[2, 0] = correlation(water_levels, rainfall)
    correlation_matrix[0, 3] = correlation_matrix[3, 0] = correlation(water_levels, evaporation)
    correlation_matrix[1, 2] = correlation_matrix[2, 1] = correlation(flow_rates, rainfall)
    correlation_matrix[1, 3] = correlation_matrix[3, 1] = correlation(flow_rates, evaporation)
    correlation_matrix[2, 3] = correlation_matrix[3, 2] = correlation(rainfall, evaporation)
    
    # 创建相关性热力图
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix,
        x=metrics,
        y=metrics,
        colorscale='RdBu',
        zmid=0,  # 使0相关性为中间颜色
        text=[[f"{val:.2f}" for val in row] for row in correlation_matrix],
        hovertemplate='%{y} 与 %{x} 的相关性: %{text}<extra></extra>',
        showscale=True
    ))
    
    fig.update_layout(
        title='水文指标相关性分析',
        height=600,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

def create_3d_surface_visualization(data):
    """创建3D曲面图可视化"""
    import numpy as np
    from scipy import interpolate
    
    # 准备3D数据
    x = np.array(range(len(data['timestamps'])))  # 时间索引
    y = np.array(range(10))  # 模拟10个不同位置的测量点
    
    # 创建模拟的z数据（水位在不同位置的变化）
    base_water_levels = np.array(data['water_levels'])
    z_original = []
    
    for i in range(10):
        # 使用更平滑的变化函数
        variation = 0.05 * i * np.exp(-0.5 * ((np.array(x) - len(x)/2) / (len(x)/4))**2)
        z_original.append(base_water_levels + variation)
    
    z_original = np.array(z_original)
    
    # 创建更密集的网格进行插值
    x_new = np.linspace(0, len(x)-1, len(x)*5)
    y_new = np.linspace(0, 9, 50)
    
    # 使用二维样条插值
    f = interpolate.RectBivariateSpline(y, x, z_original)
    
    # 创建网格
    X_new, Y_new = np.meshgrid(x_new, y_new)
    Z_new = f(y_new, x_new)
    
    # 创建平滑的曲面
    fig = go.Figure(data=[go.Surface(
        z=Z_new, 
        x=X_new, 
        y=Y_new,
        colorscale='Blues',
        contours={
            "z": {"show": True, "start": min(base_water_levels), "end": max(base_water_levels), "size": 0.01}
        }
    )])
    
    # 更新布局，增加更多交互性
    fig.update_layout(
        title='水位3D曲面图（插值平滑）',
        scene=dict(
            xaxis_title='时间',
            yaxis_title='位置',
            zaxis_title='水位(m)',
            # 调整z轴范围，使水位变化更明显
            zaxis=dict(range=[min(base_water_levels) * 0.99, max(base_water_levels) * 1.01]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1)),
            dragmode='turntable'
        ),
        height=700,
        margin=dict(l=65, r=50, b=65, t=90),
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="重置视图",
                        method="relayout",
                        args=[{"scene.camera": dict(eye=dict(x=1.5, y=1.5, z=1))}]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 10},
                showactive=False,
                x=0.1,
                y=0
            )
        ]
    )
    
    return fig

def create_radar_visualization(data):
    """创建雷达图可视化"""
    # 获取最新数据
    latest_water = data['water_levels'][-1] if data['water_levels'] else 0
    latest_flow = data['flow_rates'][-1] if data['flow_rates'] else 0
    latest_rain = data['rainfall'][-1] if data['rainfall'] else 0
    latest_evap = data['evaporation'][-1] if data['evaporation'] else 0
    
    # 根据统计数据设置各指标的警戒值
    warning_water = 2.7  # 水位警戒值，单位：m（略高于最大值2.501）
    warning_flow = 55.0  # 流量警戒值，单位：m³/s（略高于最大值51.155）
    warning_rain = 3.5   # 降水量警戒值，单位：mm（略高于最大值2.843）
    warning_evap = 0.05  # 蒸发量警戒值，单位：mm（略高于最大值0.040）
    
    # 计算指标占比（相对于各自的警戒值）
    water_percent = min(latest_water / warning_water * 100, 100)
    flow_percent = min(latest_flow / warning_flow * 100, 100)
    rain_percent = min(latest_rain / warning_rain * 100, 100)
    evap_percent = min(latest_evap / warning_evap * 100, 100)
    
    # 准备显示的文本标签（包含实际值和警戒值）
    water_text = f"水位: {latest_water:.3f}/{warning_water:.1f}m"
    flow_text = f"流量: {latest_flow:.3f}/{warning_flow:.1f}m³/s"
    rain_text = f"降水量: {latest_rain:.3f}/{warning_rain:.1f}mm"
    evap_text = f"蒸发量: {latest_evap:.4f}/{warning_evap:.3f}mm"
    
    fig = go.Figure()
    
    # 添加当前状态
    fig.add_trace(go.Scatterpolar(
        r=[water_percent, flow_percent, rain_percent, evap_percent, water_percent],
        theta=['水位', '流量', '降水量', '蒸发量', '水位'],
        fill='toself',
        name='当前状态',
        line_color='rgb(0, 128, 255)',
        fillcolor='rgba(0, 128, 255, 0.2)',
        text=[water_text, flow_text, rain_text, evap_text, water_text],
        hovertemplate='%{text}<br>占比: %{r:.1f}%<extra></extra>'
    ))
    
    # 添加警戒线（统一为100%，表示达到各自的警戒值）
    fig.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100, 100],
        theta=['水位', '流量', '降水量', '蒸发量', '水位'],
        line=dict(color='red', dash='dash'),
        name='警戒线'
    ))
    
    # 添加注意线（80%警戒值）
    fig.add_trace(go.Scatterpolar(
        r=[80, 80, 80, 80, 80],
        theta=['水位', '流量', '降水量', '蒸发量', '水位'],
        line=dict(color='orange', dash='dot'),
        name='注意线'
    ))
    
    # 添加平均值线
    avg_water = 2.500  # 水位平均值
    avg_flow = 50.331  # 流量平均值
    avg_rain = 0.818   # 降水量平均值
    avg_evap = 0.028   # 蒸发量平均值
    
    avg_water_percent = min(avg_water / warning_water * 100, 100)
    avg_flow_percent = min(avg_flow / warning_flow * 100, 100)
    avg_rain_percent = min(avg_rain / warning_rain * 100, 100)
    avg_evap_percent = min(avg_evap / warning_evap * 100, 100)
    
    fig.add_trace(go.Scatterpolar(
        r=[avg_water_percent, avg_flow_percent, avg_rain_percent, avg_evap_percent, avg_water_percent],
        theta=['水位', '流量', '降水量', '蒸发量', '水位'],
        line=dict(color='green', dash='dot'),
        name='平均值'
    ))
    
    fig.update_layout(
        title='水文指标雷达图',
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix='%',  # 添加百分比符号
                tickvals=[0, 20, 40, 60, 80, 100]
            )
        ),
        showlegend=True,
        height=600,
        annotations=[
            dict(
                x=0.5, y=-0.1,
                xref='paper', yref='paper',
                text='注：百分比表示当前值占警戒值的比例，警戒值基于历史数据设定',
                showarrow=False
            )
        ]
    )
    
    return fig

def create_map_visualization(data):
    """创建地图可视化"""
    # 模拟几个水文站点的位置（杭州附近）
    stations = [
        {"name": "站点1", "lat": 30.25, "lon": 120.15, "water_level": data['water_levels'][-1] if data['water_levels'] else 0},
        {"name": "站点2", "lat": 30.28, "lon": 120.12, "water_level": data['water_levels'][-1] * 0.9 if data['water_levels'] else 0},
        {"name": "站点3", "lat": 30.22, "lon": 120.18, "water_level": data['water_levels'][-1] * 1.1 if data['water_levels'] else 0},
        {"name": "站点4", "lat": 30.20, "lon": 120.10, "water_level": data['water_levels'][-1] * 0.95 if data['water_levels'] else 0},
    ]
    
    # 创建地图
    fig = go.Figure()
    
    # 添加站点标记
    for station in stations:
        # 根据水位设置颜色
        if station["water_level"] > 4.0:
            color = "red"
        elif station["water_level"] > 3.0:
            color = "orange"
        else:
            color = "green"
            
        fig.add_trace(go.Scattermapbox(
            lat=[station["lat"]],
            lon=[station["lon"]],
            mode='markers+text',
            marker=dict(
                size=15,
                color=color
            ),
            text=f"{station['name']}: {station['water_level']:.2f}m",
            textposition="top center",
            name=station["name"]
        ))
    
    # 更新布局，使用Carto地图样式（不需要令牌）
    fig.update_layout(
        title='水文站点地图',
        mapbox=dict(
            style="carto-positron",  # 使用Carto样式，不需要令牌
            center=dict(lat=30.25, lon=120.15),
            zoom=11
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def create_animation_visualization(data):
    """创建时间轴动画可视化"""
    fig = go.Figure()
    
    # 添加水位数据帧
    frames = []
    for i in range(len(data['timestamps'])):
        frame = go.Frame(
            data=[
                go.Scatter(
                    x=data['timestamps'][:i+1],
                    y=data['water_levels'][:i+1],
                    mode='lines+markers',
                    line=dict(color='blue', width=2),
                    name='水位'
                )
            ],
            name=str(i)
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 设置初始数据
    fig.add_trace(
        go.Scatter(
            x=[data['timestamps'][0]],
            y=[data['water_levels'][0]],
            mode='lines+markers',
            line=dict(color='blue', width=2),
            name='水位'
        )
    )
    
    # 添加播放按钮
    # 计算水位的最小值和最大值
    min_water = min(data['water_levels']) if data['water_levels'] else 0
    max_water = max(data['water_levels']) if data['water_levels'] else 1
    # 计算适当的y轴范围，使变化更明显
    y_min = min_water - (max_water - min_water) * 0.1
    y_max = max_water + (max_water - min_water) * 0.1
    
    fig.update_layout(
        title='水位变化动画',
        xaxis=dict(range=[min(data['timestamps']), max(data['timestamps'])]),
        yaxis=dict(range=[y_min, y_max]),
        updatemenus=[dict(
            type="buttons",
            buttons=[dict(
                label="播放",
                method="animate",
                args=[None, {"frame": {"duration": 100, "redraw": True}, "fromcurrent": True}]
            )]
        )],
        height=500
    )
    
    return fig