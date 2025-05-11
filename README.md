# 智慧水利第九组作业

---
stackedit:
  mermaid: true
  disableHtmlSanitization: true
---
|作者|邓菲、夏浩天、刘涛|
核心价值：通过水文模型仿真与实时数据分析，实现洪水预警和水利设施智能调控

# 项目结构 📂
hydro-system/

├── data_collection.py # 数据采集与仿真核心

├── check_database.py # 数据库操作工具

├── decision_support.py # 风险评估算法

├── hydro_web.py # Web应用入口

├── visualization2.py # 高级可视化模块

└── templates/ # Flask网页模板

## 功能特性 ✨

多源数据采集（API+仿真）

实时风险评估与分级预警

动态可视化仪表盘

数据生命周期管理

用户权限控制系统

## 技术栈 🛠️

模块 技术实现

数据采集 Requests + 自定义水文模型

数据存储 MySQL 8.0 + 自动清理机制

决策引擎 多级阈值预警算法

可视化 Plotly + Flask 模板引擎

部署 Waitress WSGI 服务器


##  系统架构
graph TD
    A[用户访问] --> B{权限验证}
    B -->|通过| C[Web界面]
    B -->|失败| D[登录页面]
    C --> E[数据采集模块]
    C --> F[可视化模块]
    E --> G[(MySQL数据库)]
    F --> G
    G --> H[决策支持模块]
    H --> C
    H --> I[预警系统]
    
    style A fill:#4CAF50,stroke:#388E3C
    style G fill:#2196F3,stroke:#1976D2
    style I fill:#F44336,stroke:#D32F2F


## 快速开始 🚀

环境要求

Python 3.9+

  

MySQL 8.0+

  

内存 ≥ 4GB

## 贡献指南 🤝
1.遵循 PEP8 编码规范

2.新增功能需包含单元测试

3.数据库变更需提交 migration 脚本

4.使用类型注解提升代码可读性



# 许可证 📄
本项目采用 MIT License

