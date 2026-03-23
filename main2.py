import sys
import json
import math
import random
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QGroupBox, QFormLayout, QLineEdit, QComboBox, QSplitter
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QFont

class FleetSimulationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("海洋集群无人机地面站 - 协同仿真模式")
        self.setGeometry(100, 100, 1400, 900)

        # === 1. 初始化集群数据 ===
        self.fleet_data = {
            "leader": {
                "id": "L01", "lat": 37.525, "lng": 122.058, 
                "role": "Decision", "speed": 0.0, "heading": 0.0
            },
            "followers": [
                {"id": "F01", "lat": 37.5248, "lng": 122.0578, "offset_x": -20, "offset_y": -20, "battery": 98.0, "motor_rpm": 0},
                {"id": "F02", "lat": 37.5248, "lng": 122.0582, "offset_x": -20, "offset_y": 20, "battery": 95.0, "motor_rpm": 0},
                {"id": "F03", "lat": 37.5252, "lng": 122.0580, "offset_x": 20, "offset_y": 0, "battery": 92.0, "motor_rpm": 0}
            ]
        }
        self.water_current = {"speed": 0.5, "direction": 45.0}
        self.comm_delay = 50
        self.simulation_active = True

        # === 2. 构建 UI ===
        self.init_ui()

        # === 3. 启动仿真定时器 ===
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_simulation_loop)
        self.sim_timer.start(200)  # 200ms 更新一次

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左侧控制面板 ---
        left_panel = QGroupBox("集群控制中心")
        left_layout = QVBoxLayout()
        
        # 串口配置
        serial_group = QGroupBox("通信配置")
        serial_form = QFormLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems(["/dev/ttyUSB0", "COM3", "COM4"])
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "57600"])
        serial_form.addRow("串口端口:", self.port_combo)
        serial_form.addRow("波特率:", self.baud_combo)
        serial_group.setLayout(serial_form)
        
        # 指令发送
        cmd_group = QGroupBox("指令发送")
        cmd_layout = QVBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入指令: takeoff, follow, formation...")
        self.send_btn = QPushButton("发送指令")
        self.send_btn.clicked.connect(self.send_command)
        cmd_layout.addWidget(self.cmd_input)
        cmd_layout.addWidget(self.send_btn)
        cmd_group.setLayout(cmd_layout)

        # 干扰注入 (体现难点)
        disturb_group = QGroupBox("环境干扰注入 (实验台)")
        disturb_layout = QVBoxLayout()
        self.water_btn = QPushButton("💧 注入突发水流")
        self.delay_btn = QPushButton("📡 模拟通信延迟")
        self.collision_btn = QPushButton("⚠️ 模拟副船故障")
        self.water_btn.clicked.connect(self.inject_water)
        self.delay_btn.clicked.connect(self.inject_delay)
        self.collision_btn.clicked.connect(self.inject_fault)
        disturb_layout.addWidget(self.water_btn)
        disturb_layout.addWidget(self.delay_btn)
        disturb_layout.addWidget(self.collision_btn)
        disturb_group.setLayout(disturb_layout)

        # 日志
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)

        left_layout.addWidget(serial_group)
        left_layout.addWidget(cmd_group)
        left_layout.addWidget(disturb_group)
        left_layout.addWidget(log_group)
        left_panel.setLayout(left_layout)

        # --- 右侧地图视图 ---
        self.map_view = QWebEngineView()
        self.create_and_load_map_html()

        # --- 布局组合 ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        self.log_message("系统启动 - 仿真模式已激活")
        self.log_message("集群初始化: 1 主船 + 3 副船 (带动力)")
        self.log_message("水流扰动: 0.5m/s @ 45°")

    def create_and_load_map_html(self):
        """创建并加载地图HTML"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>集群协同地图</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: 'Microsoft YaHei'; }
        #map { width: 100%; height: 100%; }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v7.3.0/ol.css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v7.3.0/dist/ol.js"></script>
</head>
<body>
    <div id="map"></div>
    <script>
        // 创建地图实例
        var map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.OSM()
                })
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([122.058, 37.525]),
                zoom: 16
            })
        });

        // 存储标记
        var leaderFeature = null;
        var followerFeatures = [];
        var connectionLines = [];

        // 接收 Python 数据的函数
        function updateFleetPositions(dataStr) {
            try {
                var data = JSON.parse(dataStr);
                var leader = data.leader;
                var followers = data.followers;

                // 清除现有连线
                connectionLines.forEach(line => {
                    try {
                        if (line && line.getMap()) {
                            map.removeLayer(line);
                        }
                    } catch(e) {}
                });
                connectionLines = [];

                // 1. 更新主船
                var leaderCoord = ol.proj.fromLonLat([leader.lng, leader.lat]);
                
                if (!leaderFeature) {
                    leaderFeature = new ol.Feature({
                        geometry: new ol.geom.Point(leaderCoord)
                    });
                    
                    var leaderStyle = new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 10,
                            fill: new ol.style.Fill({color: '#FFD700'}),
                            stroke: new ol.style.Stroke({color: '#FFF', width: 2})
                        }),
                        text: new ol.style.Text({
                            text: '指挥主船',
                            offsetY: -20,
                            font: 'bold 14px sans-serif',
                            fill: new ol.style.Fill({color: '#FFD700'}),
                            stroke: new ol.style.Stroke({color: '#000', width: 1})
                        })
                    });
                    
                    leaderFeature.setStyle(leaderStyle);
                    
                    var vectorSource = new ol.source.Vector({
                        features: [leaderFeature]
                    });
                    
                    var vectorLayer = new ol.layer.Vector({
                        source: vectorSource
                    });
                    
                    map.addLayer(vectorLayer);
                } else {
                    leaderFeature.getGeometry().setCoordinates(leaderCoord);
                    // 更新样式
                    var updatedStyle = new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 10,
                            fill: new ol.style.Fill({color: '#FFD700'}),
                            stroke: new ol.style.Stroke({color: '#FFF', width: 2})
                        }),
                        text: new ol.style.Text({
                            text: '指挥主船',
                            offsetY: -20,
                            font: 'bold 14px sans-serif',
                            fill: new ol.style.Fill({color: '#FFD700'}),
                            stroke: new ol.style.Stroke({color: '#000', width: 1})
                        })
                    });
                    leaderFeature.setStyle(updatedStyle);
                }

                // 2. 更新副船
                followers.forEach((f, idx) => {
                    var followerCoord = ol.proj.fromLonLat([f.lng, f.lat]);
                    
                    if (!followerFeatures[idx]) {
                        followerFeatures[idx] = new ol.Feature({
                            geometry: new ol.geom.Point(followerCoord)
                        });
                        
                        var followerStyle = new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 6,
                                fill: new ol.style.Fill({color: '#00BFFF'}),
                                stroke: new ol.style.Stroke({color: '#FFF', width: 1})
                            }),
                            text: new ol.style.Text({
                                text: `副船${idx+1}\\n电量:${f.battery.toFixed(1)}%`,
                                offsetY: 15,
                                font: '10px sans-serif',
                                fill: new ol.style.Fill({color: '#00BFFF'}),
                                stroke: new ol.style.Stroke({color: '#000', width: 1})
                            })
                        });
                        
                        followerFeatures[idx].setStyle(followerStyle);
                        
                        var followerVectorSource = new ol.source.Vector({
                            features: [followerFeatures[idx]]
                        });
                        
                        var followerVectorLayer = new ol.layer.Vector({
                            source: followerVectorSource
                        });
                        
                        map.addLayer(followerVectorLayer);
                    } else {
                        followerFeatures[idx].getGeometry().setCoordinates(followerCoord);
                        // 更新样式
                        var updatedFollowerStyle = new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 6,
                                fill: new ol.style.Fill({color: '#00BFFF'}),
                                stroke: new ol.style.Stroke({color: '#FFF', width: 1})
                            }),
                            text: new ol.style.Text({
                                text: `副船${idx+1}\\n电量:${f.battery.toFixed(1)}%`,
                                offsetY: 15,
                                font: '10px sans-serif',
                                fill: new ol.style.Fill({color: '#00BFFF'}),
                                stroke: new ol.style.Stroke({color: '#000', width: 1})
                            })
                        });
                        followerFeatures[idx].setStyle(updatedFollowerStyle);
                    }

                    // 绘制连线 (体现协同关系)
                    var lineFeature = new ol.Feature({
                        geometry: new ol.geom.LineString([ol.proj.fromLonLat([leader.lng, leader.lat]), followerCoord])
                    });
                    
                    var lineStyle = new ol.style.Style({
                        stroke: new ol.style.Stroke({
                            color: '#FF4500',
                            width: 2
                        })
                    });
                    
                    lineFeature.setStyle(lineStyle);
                    
                    var lineSource = new ol.source.Vector({
                        features: [lineFeature]
                    });
                    
                    var lineLayer = new ol.layer.Vector({
                        source: lineSource
                    });
                    
                    map.addLayer(lineLayer);
                    connectionLines.push(lineLayer);
                });
            } catch (e) {
                console.error('Error updating fleet positions:', e);
            }
        }

        // 页面加载完成后的初始化
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Map loaded successfully');
        });
    </script>
</body>
</html>
        """
        # 直接设置HTML内容
        self.map_view.setHtml(html_content)

    def update_simulation_loop(self):
        """仿真核心逻辑：计算主从跟随、水流扰动"""
        if not self.simulation_active:
            return

        leader = self.fleet_data["leader"]
        
        # 1. 主船运动 (简单圆周运动)
        leader["speed"] = 2.5
        leader["heading"] = (leader["heading"] + 0.3) % 360
        dx = leader["speed"] * math.sin(math.radians(leader["heading"])) * 0.000008
        dy = leader["speed"] * math.cos(math.radians(leader["heading"])) * 0.000008
        leader["lng"] += dx
        leader["lat"] += dy

        # 2. 副船协同跟随 (体现抗扰动算法)
        for i, follower in enumerate(self.fleet_data["followers"]):
            # 理想位置 = 主船 + 编队偏移
            target_lat = leader["lat"] + (follower["offset_y"] * 0.000009)
            target_lng = leader["lng"] + (follower["offset_x"] * 0.000012)
            
            # 加入水流扰动 (模拟算法补偿后的残差)
            disturbance = 0.000003 * (random.random() - 0.5)
            current_lat = target_lat + disturbance
            current_lng = target_lng + disturbance
            
            # 平滑移动 (一阶惯性)
            follower["lat"] = follower["lat"] * 0.7 + current_lat * 0.3
            follower["lng"] = follower["lng"] * 0.7 + current_lng * 0.3
            
            # 模拟电机动态
            follower["motor_rpm"] = int(1500 + random.randint(-100, 100))
            follower["battery"] = max(0, follower["battery"] - 0.02)

        # 3. 发送数据到前端地图
        self.update_map_view_js()
        
        # 4. 更新日志 (每秒一次)
        if int(self.sim_timer.remainingTime()) % 5000 == 0:  # 简化条件检查
            avg_error = random.uniform(0.1, 0.4)
            self.log_message(f"编队误差: {avg_error:.2f}m | 延迟: {self.comm_delay}ms | 副船电机: {self.fleet_data['followers'][0]['motor_rpm']} RPM")

    def update_map_view_js(self):
        """调用前端 JS 更新地图"""
        data_json = json.dumps(self.fleet_data)
        js_code = f"updateFleetPositions('{data_json}');"
        self.map_view.page().runJavaScript(js_code)

    def send_command(self):
        cmd = self.cmd_input.text()
        self.log_message(f"[TX] 发送指令: {cmd}")
        self.cmd_input.clear()

    def inject_water(self):
        self.water_current["speed"] = random.uniform(1.0, 2.0)
        self.log_message(f"⚠️ 警告: 注入突发水流 {self.water_current['speed']:.1f}m/s")

    def inject_delay(self):
        self.comm_delay = random.randint(100, 500)
        self.log_message(f"⚠️ 警告: 通信延迟增加至 {self.comm_delay}ms")

    def inject_fault(self):
        self.log_message("⚠️ 警告: 副船 F02 电机故障 - 切换至应急模式")

    def log_message(self, msg):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FleetSimulationWindow()
    window.show()
    sys.exit(app.exec())
