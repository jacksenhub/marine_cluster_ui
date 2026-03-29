# marine_cluster_ui 项目
海洋集群无人机地面站系统 - 多版本实现

## 📁 文件说明

### 1. `main.py` - 水池定位可视化系统
- 类名：`FleetSimulationWindow`
- 专注于实验室水池环境定位可视化
- 使用PyQt5框架
- 包含地图显示、状态监控、轨迹绘制功能

### 2. `marine_cluster_final.py` - 完整地面站系统（推荐）
- 类名：`MarineClusterUIVisualization`
- 完整的海洋集群无人机地面站功能
- 基于`openclawdoit.py`修复的PyQt5兼容版本
- 包含功能：
  - 串口通信（真实串口+仿真模式）
  - 地图可视化（OpenLayers）
  - 3D集群显示
  - 状态监控表格
  - 环境干扰注入
  - 系统日志

### 3. `openclawdoit.py` - 原版地面站系统
- 类名：`MarineClusterUIVisualization`
- 与`marine_cluster_final.py`功能相同
- 使用PyQt6框架（需要PyQt6环境）
- 供参考和未来升级使用

## 🚀 快速开始

```bash
# 安装依赖
pip install PyQt5 PyQtWebEngine pyserial

# 运行推荐版本
python3 marine_cluster_final.py

# 运行水池版本
python3 main.py
```

## 🔧 功能特点

- **多版本实现**：针对不同场景的多个实现版本
- **完整功能**：通信、可视化、监控、控制一体化
- **仿真模式**：无需硬件即可测试所有功能
- **跨平台**：支持Windows/Linux/macOS
- **开源可扩展**：模块化设计，易于二次开发

## 📊 版本关系

```
openclawdoit.py (PyQt6原版，97.6%相同)
    ↓
marine_cluster_final.py (PyQt5转换版，推荐使用)
    ↑
main.py (独立实现，12.7%相同，水池专用)
```

## 📝 更新日志

### 2026-03-29
- 新增`marine_cluster_final.py`整合版本
- 优化`main.py`地图加载逻辑
- 修复JavaScript执行错误
- 改进用户体验

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/9cc51580-ed8f-4600-9c92-a0feb4c7991b" />

