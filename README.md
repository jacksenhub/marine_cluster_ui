# marine_cluster_ui 项目
海洋集群无人机地面站系统

## 📁 文件说明

### 1. `main.py` - 水池定位可视化系统（推荐使用）
- **类名**：`FleetSimulationWindow`
- **功能**：专注于实验室水池环境定位可视化
- **框架**：PyQt5
- **主要功能**：
  - 地图显示与交互
  - 无人机状态实时监控
  - 轨迹绘制与历史回放
  - 水池环境模拟
  - 数据记录与分析

### 2. `openclawdoit.py` - 原版地面站系统（供参考）
- **类名**：`MarineClusterUIVisualization`
- **功能**：完整的海洋集群无人机地面站功能
- **框架**：PyQt6（需要PyQt6环境）
- **主要功能**：
  - 串口通信（真实串口+仿真模式）
  - 地图可视化（OpenLayers）
  - 3D集群显示
  - 状态监控表格
  - 环境干扰注入
  - 系统日志记录
- **状态**：供技术参考和未来升级使用

## 🚀 快速开始

### 安装依赖
```bash
# 基础依赖（运行main.py所需）
pip install PyQt5 PyQtWebEngine pyserial

# 如果需要运行openclawdoit.py（PyQt6版本）
pip install PyQt6 PyQt6-WebEngine
```

### 运行程序
```bash
# 运行推荐版本（水池定位可视化系统）
python3 main.py

# 运行原版地面站系统（需要PyQt6环境）
# python3 openclawdoit.py
```

## 🔧 功能特点

### 🎯 核心功能
- **实时可视化**：地图显示无人机位置和状态
- **多模式通信**：支持真实串口和仿真模式
- **状态监控**：实时显示电量、高度、速度等参数
- **轨迹记录**：自动记录飞行轨迹，支持回放

### 🛠️ 技术特性
- **模块化设计**：代码结构清晰，易于扩展
- **跨平台支持**：兼容Windows/Linux/macOS
- **仿真测试**：无需硬件即可测试所有功能
- **开源可扩展**：MIT许可证，支持二次开发

### 📊 应用场景
- 实验室水池环境无人机测试
- 海洋集群无人机协同控制
- 无人机定位与导航算法验证
- 教学与科研演示

## 📁 项目结构

```
marine_cluster_ui/
├── main.py                    # 水池定位可视化系统（主程序）
├── openclawdoit.py            # 原版地面站系统（PyQt6参考版）
├── README.md                  # 项目说明文档
├── .gitignore                 # Git忽略文件配置
├── LICENSE                    # 开源许可证
└── venv/                      # Python虚拟环境（可选）
```

## 📝 更新日志

### 2026-03-30
- **精简项目结构**：删除`marine_cluster_final.py`文件
- **更新文档**：优化README.md，反映当前项目状态
- **明确版本**：确定`main.py`为推荐使用版本

### 2026-03-29
- **新增功能**：优化`main.py`地图加载逻辑
- **修复问题**：修复JavaScript执行错误
- **改进体验**：增强用户界面和交互体验

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. **Fork本仓库**
2. **创建功能分支** (`git checkout -b feature/新功能`)
3. **提交更改** (`git commit -m '添加新功能'`)
4. **推送到分支** (`git push origin feature/新功能`)
5. **开启Pull Request**

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系与支持

- **GitHub Issues**: [问题反馈](https://github.com/jacksenhub/marine_cluster_ui/issues)
- **项目地址**: https://github.com/jacksenhub/marine_cluster_ui
- **使用说明**: 详细使用说明请参考代码注释和本文档

---

<div align="center">
  
**海洋集群无人机地面站系统** 🚁🌊

*让无人机集群控制更简单、更直观*

</div>

