#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海洋集群无人机地面站 - 完整整合版（修复语法错误）
整合了 main_simulation.py 和 main2.py 的功能，并增加无人机系统可视化
"""

import sys
import json
import math
import random
import serial
from typing import Optional
from datetime import datetime

# PyQt6 导入
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QStatusBar, QSplitter,
    QGroupBox, QFormLayout, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import (
    Qt, QUrl, QThread, pyqtSignal, QTimer
)
from PyQt6.QtGui import QFont

# ==================== 串口通信线程 ====================
class SerialThread(QThread):
    recv_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.is_running = False

    def run(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            self.is_running = True
            self.recv_signal.emit(f"串口已连接：{self.port}")
            
            while self.is_running:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        self.recv_signal.emit(data)
        except Exception as e:
            self.error_signal.emit(f"串口错误：{str(e)}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.is_running = False

    def stop(self):
        self.is_running = False
        self.wait()

    def send_data(self, data: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((data + '\n').encode('utf-8'))
            except Exception as e:
                self.error_signal.emit(f"发送失败：{str(e)}")

# ==================== 主界面类 ====================
class MarineClusterUIVisualization(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread: Optional[SerialThread] = None
        
        # 集群数据初始化
        self.fleet_data = {
            "leader": {
                "id": "L01", "lat": 37.525, "lng": 122.058, 
                "role": "Decision", "speed": 0.0, "heading": 0.0,
                "battery": 100.0, "status": "正常", "altitude": 50.0
            },
            "followers": [
                {"id": "F01", "lat": 37.5248, "lng": 122.0578, "offset_x": -20, "offset_y": -20, 
                 "battery": 98.0, "motor_rpm": 0, "status": "正常", "altitude": 45.0},
                {"id": "F02", "lat": 37.5248, "lng": 122.0582, "offset_x": -20, "offset_y": 20, 
                 "battery": 95.0, "motor_rpm": 0, "status": "正常", "altitude": 48.0},
                {"id": "F03", "lat": 37.5252, "lng": 122.0580, "offset_x": 20, "offset_y": 0, 
                 "battery": 92.0, "motor_rpm": 0, "status": "正常", "altitude": 47.0}
            ]
        }
        
        self.water_current = {"speed": 0.5, "direction": 45.0}
        self.comm_delay = 50
        self.simulation_active = True
        
        self.init_ui()
        self.init_timers()

    def init_ui(self):
        self.setWindowTitle("海洋集群无人机地面站 - 整合增强版")
        self.setGeometry(100, 100, 1400, 800)
        self.setMinimumSize(1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧控制面板
        left_panel = self._create_left_panel()
        # 右侧主区域
        right_panel = self._create_right_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 整合增强模式")

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        title_label = QLabel("集群控制中心")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 串口配置
        serial_group = QGroupBox("通信配置")
        serial_layout = QFormLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems(["/dev/ttyUSB0", "COM3", "COM4", "仿真模式"])
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "57600"])
        serial_layout.addRow("串口端口:", self.port_combo)
        serial_layout.addRow("波特率:", self.baud_combo)
        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

        # 串口控制按钮
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接串口")
        self.connect_btn.clicked.connect(self.toggle_serial)
        btn_layout.addWidget(self.connect_btn)
        
        self.send_btn = QPushButton("发送指令")
        self.send_btn.clicked.connect(self.send_serial_data)
        self.send_btn.setEnabled(False)
        btn_layout.addWidget(self.send_btn)
        layout.addLayout(btn_layout)

        # 指令输入
        cmd_group = QGroupBox("指令发送")
        cmd_layout = QVBoxLayout()
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("输入指令: takeoff, land, follow, formation, emergency")
        cmd_layout.addWidget(self.cmd_edit)
        cmd_group.setLayout(cmd_layout)
        layout.addWidget(cmd_group)

        # 干扰注入
        disturb_group = QGroupBox("环境干扰注入")
        disturb_layout = QVBoxLayout()
        self.water_btn = QPushButton("注入突发水流")
        self.delay_btn = QPushButton("模拟通信延迟")
        self.fault_btn = QPushButton("模拟副船故障")
        self.water_btn.clicked.connect(self.inject_water)
        self.delay_btn.clicked.connect(self.inject_delay)
        self.fault_btn.clicked.connect(self.inject_fault)
        disturb_layout.addWidget(self.water_btn)
        disturb_layout.addWidget(self.delay_btn)
        disturb_layout.addWidget(self.fault_btn)
        disturb_group.setLayout(disturb_layout)
        layout.addWidget(disturb_group)

        # 无人机状态表格
        status_group = QGroupBox("无人机状态监控")
        status_layout = QVBoxLayout()
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(5)
        self.status_table.setHorizontalHeaderLabels(["ID", "电量%", "状态", "高度(m)", "电机RPM"])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.status_table.setMaximumHeight(200)
        status_layout.addWidget(self.status_table)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 日志显示
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标签页
        self.tab_widget = QTabWidget()
        
        # 地图标签
        self.map_tab = QWidget()
        map_layout = QVBoxLayout(self.map_tab)
        self.load_map_engine()
        map_layout.addWidget(self.web_view)
        self.tab_widget.addTab(self.map_tab, "集群地图")
        
        # 3D可视化标签
        self.visual_tab = QWidget()
        visual_layout = QVBoxLayout(self.visual_tab)
        self._create_3d_visualization(visual_layout)
        self.tab_widget.addTab(self.visual_tab, "3D可视化")
        
        layout.addWidget(self.tab_widget)
        return panel

    def load_map_engine(self):
        self.web_view = QWebEngineView()
        self.web_page = QWebEnginePage()
        self.web_view.setPage(self.web_page)

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        # 加载简化版地图HTML
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>集群协同地图</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
        #map { width: 100%; height: 100%; }
        .info-panel {
            position: absolute; top: 10px; right: 10px;
            background: rgba(255,255,255,0.9); padding: 10px;
            border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000; font-size: 12px;
        }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v7.3.0/ol.css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v7.3.0/dist/ol.js"></script>
</head>
<body>
    <div id="map"></div>
    <div class="info-panel">
        <div>主船: <span id="leader-info">等待数据...</span></div>
        <div>副船数量: <span id="follower-count">3</span></div>
        <div>编队误差: <span id="formation-error">0.00m</span></div>
    </div>
    <script>
        var map = new ol.Map({
            target: 'map',
            layers: [new ol.layer.Tile({source: new ol.source.OSM()})],
            view: new ol.View({
                center: ol.proj.fromLonLat([122.058, 37.525]),
                zoom: 16
            })
        });

        var leaderFeature = null;
        var followerFeatures = [];

        function updateFleetPositions(dataStr) {
            try {
                var data = JSON.parse(dataStr);
                var leader = data.leader;
                var followers = data.followers;

                // 更新主船
                var leaderCoord = ol.proj.fromLonLat([leader.lng, leader.lat]);
                if (!leaderFeature) {
                    leaderFeature = new ol.Feature({geometry: new ol.geom.Point(leaderCoord)});
                    var leaderStyle = new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 12, fill: new ol.style.Fill({color: '#FFD700'}),
                            stroke: new ol.style.Stroke({color: '#FFF', width: 3})
                        })
                    });
                    leaderFeature.setStyle(leaderStyle);
                    var vectorSource = new ol.source.Vector({features: [leaderFeature]});
                    var vectorLayer = new ol.layer.Vector({source: vectorSource});
                    map.addLayer(vectorLayer);
                } else {
                    leaderFeature.getGeometry().setCoordinates(leaderCoord);
                }

                document.getElementById('leader-info').textContent = 
                    leader.altitude.toFixed(1) + 'm | ' + leader.battery.toFixed(1) + '%';

                // 更新副船
                followers.forEach((f, idx) => {
                    var followerCoord = ol.proj.fromLonLat([f.lng, f.lat]);
                    if (!followerFeatures[idx]) {
                        followerFeatures[idx] = new ol.Feature({geometry: new ol.geom.Point(followerCoord)});
                        var followerStyle = new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: 8, fill: new ol.style.Fill({color: '#00BFFF'}),
                                stroke: new ol.style.Stroke({color: '#FFF', width: 2})
                            })
                        });
                        followerFeatures[idx].setStyle(followerStyle);
                        var followerSource = new ol.source.Vector({features: [followerFeatures[idx]]});
                        var followerLayer = new ol.layer.Vector({source: followerSource});
                        map.addLayer(followerLayer);
                    } else {
                        followerFeatures[idx].getGeometry().setCoordinates(followerCoord);
                    }
                });

            } catch (e) {
                console.error('Error updating fleet positions:', e);
            }
        }
    </script>
</body>
</html>
        """
        self.web_view.setHtml(html_content)
        self.web_page.loadFinished.connect(self.on_map_loaded)

    def _create_3d_visualization(self, layout):
        """创建简化的3D可视化面板"""
        self.web_3d_view = QWebEngineView()
        
        html_3d = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>无人机3D可视化</title>
    <style>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
        #container { width: 100%; height: 100%; }
    </style>
    <script>
        // 简化的3D可视化
        document.addEventListener('DOMContentLoaded', function() {
            var container = document.getElementById('container');
            container.innerHTML = '<div style="padding: 20px; font-family: Arial;">' +
                '<h3>无人机3D集群可视化</h3>' +
                '<p>3D可视化功能需要Three.js库支持</p>' +
                '<p>主船高度: <span id="leader-altitude">50.0m</span></p>' +
                '<p>副船数量: <span id="follower-count-3d">3</span></p>' +
                '<p>注：这是一个简化的3D可视化界面</p>' +
                '</div>';
        });
        
        function update3DPositions(dataStr) {
            try {
                var data = JSON.parse(dataStr);
                var leader = data.leader;
                var followers = data.followers;
                
                document.getElementById('leader-altitude').textContent = leader.altitude.toFixed(1) + 'm';
                document.getElementById('follower-count-3d').textContent = followers.length;
                
            } catch(e) {
                console.error('3D update error:', e);
            }
        }
    </script>
</head>
<body>
    <div id="container"></div>
</body>
</html>
        """
        
        self.web_3d_view.setHtml(html_3d)
        layout.addWidget(self.web_3d_view)

    def init_timers(self):
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_simulation_loop)
        self.sim_timer.start(200)
        
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(1000)

    def update_simulation_loop(self):
        if not self.simulation_active:
            return

        leader = self.fleet_data["leader"]
        
        # 主船运动
        leader["speed"] = 2.5
        leader["heading"] = (leader["heading"] + 0.3) % 360
        dx = leader["speed"] * math.sin(math.radians(leader["heading"])) * 0.000008
        dy = leader["speed"] * math.cos(math.radians(leader["heading"])) * 0.000008
        leader["lng"] += dx
        leader["lat"] += dy
        
        leader["altitude"] = 50 + random.uniform(-2, 2)
        leader["battery"] = max(0, leader["battery"] - 0.01)

        # 副船协同跟随
        for i, follower in enumerate(self.fleet_data["followers"]):
            target_lat = leader["lat"] + (follower["offset_y"] * 0.000009)
            target_lng = leader["lng"] + (follower["offset_x"] * 0.000012)
            
            disturbance = self.water_current["speed"] * 0.000003 * (random.random() - 0.5)
            current_lat = target_lat + disturbance
            current_lng = target_lng + disturbance
            
            follower["lat"] = follower["lat"] * 0.7 + current_lat * 0.3
            follower["lng"] = follower["lng"] * 0.7 + current_lng * 0.3
            
            follower["altitude"] = leader["altitude"] + random.uniform(-3, 3)
            follower["motor_rpm"] = int(1500 + random.randint(-100, 100))
            follower["battery"] = max(0, follower["battery"] - 0.02)

        # 更新地图显示
        self.update_map_view()
        
        # 更新3D可视化
        self.update_3d_view()
        
        # 更新状态表格
        self.update_status_table()

    def update_map_view(self):
        data_json = json.dumps(self.fleet_data)
        js_code = f"updateFleetPositions('{data_json}');"
        self.web_view.page().runJavaScript(js_code)

    def update_3d_view(self):
        data_json = json.dumps(self.fleet_data)
        js_code = f"update3DPositions('{data_json}');"
        self.web_3d_view.page().runJavaScript(js_code)

    def update_status_table(self):
        self.status_table.setRowCount(len(self.fleet_data["followers"]) + 1)
        
        # 更新主船状态
        leader = self.fleet_data["leader"]
        self.status_table.setItem(0, 0, QTableWidgetItem(leader["id"]))
        self.status_table.setItem(0, 1, QTableWidgetItem(f"{leader['battery']:.1f}%"))
        self.status_table.setItem(0, 2, QTableWidgetItem(leader["status"]))
        self.status_table.setItem(0, 3, QTableWidgetItem(f"{leader['altitude']:.1f}"))
        self.status_table.setItem(0, 4, QTableWidgetItem("N/A"))
        
        # 更新副船状态
        for i, follower in enumerate(self.fleet_data["followers"]):
            row = i + 1
            self.status_table.setItem(row, 0, QTableWidgetItem(follower["id"]))
            self.status_table.setItem(row, 1, QTableWidgetItem(f"{follower['battery']:.1f}%"))
            self.status_table.setItem(row, 2, QTableWidgetItem(follower["status"]))
            self.status_table.setItem(row, 3, QTableWidgetItem(f"{follower['altitude']:.1f}"))
            self.status_table.setItem(row, 4, QTableWidgetItem(str(follower["motor_rpm"])))

    def update_status_display(self):
        avg_battery = (self.fleet_data["leader"]["battery"] + 
                      sum(f["battery"] for f in self.fleet_data["followers"])) / 4
        self.status_bar.showMessage(
            f"平均电量: {avg_battery:.1f}% | 通信延迟: {self.comm_delay}ms | "
            f"水流速度: {self.water_current['speed']:.1f}m/s"
        )

    def toggle_serial(self):
        if self.serial_thread and self.serial_thread.is_running:
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("连接串口")
            self.send_btn.setEnabled(False)
            self.log_message("串口已断开")
            self.status_bar.showMessage("串口已断开 - 仿真模式")
        else:
            try:
                port = self.port_combo.currentText()
                if port == "仿真模式":
                    self.log_message("进入仿真模式，无需真实串口")
                    self.connect_btn.setText("断开仿真")
                    self.send_btn.setEnabled(True)
                    self.status_bar.showMessage("仿真模式已激活")
                else:
                    baudrate = int(self.baud_combo.currentText())
                    self.serial_thread = SerialThread(port, baudrate)
                    self.serial_thread.recv_signal.connect(self.on_serial_recv)
                    self.serial_thread.error_signal.connect(self.on_serial_error)
                    self.serial_thread.start()
                    self.connect_btn.setText("断开串口")
                    self.send_btn.setEnabled(True)
                    self.status_bar.showMessage(f"串口已连接：{port}")
            except ValueError:
                self.log_message("错误：波特率必须是数字")
            except Exception as e:
                self.log_message(f"串口连接失败：{str(e)}")

    def send_serial_data(self):
        data = self.cmd_edit.text().strip()
        if not data:
            self.log_message("错误：请输入要发送的指令")
            return
        
        if self.port_combo.currentText() == "仿真模式":
            self.log_message(f"[仿真] 发送指令: {data}")
            if data.lower() == "takeoff":
                for drone in self.fleet_data["followers"]:
                    drone["altitude"] = 50
                self.log_message("仿真：所有无人机起飞至50米高度")
            elif data.lower() == "land":
                for drone in self.fleet_data["followers"]:
                    drone["altitude"] = 5
                self.log_message("仿真：所有无人机降落至5米高度")
            elif data.lower().startswith("formation"):
                self.log_message("仿真：切换编队队形")
            elif data.lower() == "emergency":
                self.fleet_data["followers"][1]["status"] = "故障"
                self.log_message("仿真：副船F02进入故障状态")
        elif self.serial_thread and self.serial_thread.is_running:
            self.serial_thread.send_data(data)
            self.log_message(f"发送：{data}")
        
        self.cmd_edit.clear()

    def on_serial_recv(self, data: str):
        self.log_message(f"接收：{data}")

    def on_serial_error(self, error: str):
        self.log_message(f"错误：{error}")
        self.connect_btn.setText("连接串口")
        self.send_btn.setEnabled(False)
        self.status_bar.showMessage("串口错误")

    def on_map_loaded(self, success: bool):
        if success:
            self.log_message("地图加载成功")
            self.status_bar.showMessage("地图加载完成")
        else:
            self.log_message("地图加载失败")
            self.status_bar.showMessage("地图加载失败")

    def inject_water(self):
        self.water_current["speed"] = random.uniform(1.0, 2.0)
        self.log_message(f"警告：注入突发水流 {self.water_current['speed']:.1f}m/s")

    def inject_delay(self):
        self.comm_delay = random.randint(100, 500)
        self.log_message(f"警告：通信延迟增加至 {self.comm_delay}ms")

    def inject_fault(self):
        fault_index = random.randint(0, len(self.fleet_data["followers"]) - 1)
        self.fleet_data["followers"][fault_index]["status"] = "故障"
        self.fleet_data["followers"][fault_index]["motor_rpm"] = 0
        self.log_message(f"警告：副船 {self.fleet_data['followers'][fault_index]['id']} 电机故障")

    def log_message(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
        self.sim_timer.stop()
        self.status_timer.stop()
        event.accept()

# ==================== 程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarineClusterUIVisualization()
    window.show()
    sys.exit(app.exec())
