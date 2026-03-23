#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marine Cluster UI - 海洋集群无人机地面站仿真界面
修复 PyQt6 兼容性问题：QWebEnginePage/QWebEngineSettings 导入及使用
"""
import sys
import serial
import requests
from typing import Optional

# PyQt6 正确导入（核心修复）
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QStatusBar, QSplitter
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import (
    Qt, QUrl, QThread, pyqtSignal, QTimer
)
from PyQt6.QtGui import QFont, QIcon

# 串口通信线程（避免阻塞UI）
class SerialThread(QThread):
    recv_signal = pyqtSignal(str)  # 接收数据信号
    error_signal = pyqtSignal(str) # 错误信号

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.is_running = False

    def run(self):
        """线程运行函数"""
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
        """停止串口线程"""
        self.is_running = False
        self.wait()

    def send_data(self, data: str):
        """发送数据"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((data + '\n').encode('utf-8'))
            except Exception as e:
                self.error_signal.emit(f"发送失败：{str(e)}")

# 主界面类
class MarineClusterUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread: Optional[SerialThread] = None
        self.init_ui()
        self.init_timer()

    def init_ui(self):
        """初始化UI"""
        # 窗口基础设置
        self.setWindowTitle("海洋集群无人机地面站 - 仿真模式")
        self.setGeometry(100, 100, 1400, 800)
        self.setMinimumSize(1000, 600)

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧控制面板
        left_panel = self._create_left_panel()
        # 右侧地图面板
        right_panel = self._create_right_panel()

        # 分割器（可调整面板大小）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])  # 初始大小
        main_layout.addWidget(splitter)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 仿真模式")

    def _create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("集群控制中心")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 串口配置区
        serial_group = QWidget()
        serial_layout = QVBoxLayout(serial_group)
        serial_layout.setSpacing(8)
        
        # 串口端口输入
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("串口端口："))
        self.port_edit = QLineEdit("/dev/ttyUSB0")
        port_layout.addWidget(self.port_edit)
        serial_layout.addLayout(port_layout)

        # 波特率输入
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("波特率："))
        self.baud_edit = QLineEdit("9600")
        baud_layout.addWidget(self.baud_edit)
        serial_layout.addLayout(baud_layout)

        # 串口控制按钮
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接串口")
        self.connect_btn.clicked.connect(self.toggle_serial)
        btn_layout.addWidget(self.connect_btn)
        
        self.send_btn = QPushButton("发送指令")
        self.send_btn.clicked.connect(self.send_serial_data)
        self.send_btn.setEnabled(False)
        btn_layout.addWidget(self.send_btn)
        serial_layout.addLayout(btn_layout)

        layout.addWidget(serial_group)

        # 指令输入区
        cmd_layout = QVBoxLayout()
        cmd_layout.addWidget(QLabel("发送指令："))
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("输入无人机指令，如：takeoff, land, move 100 200")
        cmd_layout.addWidget(self.cmd_edit)
        layout.addLayout(cmd_layout)

        # 日志显示区
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("通信日志："))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addLayout(log_layout)

        # 填充空白
        layout.addStretch()

        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧地图面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 地图视图（核心修复：WebEngineSettings 使用）
        self.load_map_engine()
        layout.addWidget(self.web_view)

        return panel

    def load_map_engine(self):
        """加载地图引擎（修复 WebEngineSettings 问题）"""
        # 创建 WebEngineView 实例
        self.web_view = QWebEngineView()
        self.web_page = QWebEnginePage()
        self.web_view.setPage(self.web_page)

        # 获取并配置 WebEngine 设置（PyQt6 正确写法）
        settings = self.web_view.settings()
        # 启用JavaScript（必须）
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # 允许本地内容访问远程URL
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        # 允许本地内容访问文件
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        # 启用本地存储
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        # 加载地图（可替换为本地HTML文件或在线地图）
        # 示例1：加载在线地图（百度地图）
        self.web_view.load(QUrl("https://map.baidu.com"))
        # 示例2：加载本地地图文件（取消注释并替换路径）
        # self.web_view.load(QUrl.fromLocalFile("/path/to/your/map.html"))

        # 页面加载完成信号
        self.web_page.loadFinished.connect(self.on_map_loaded)

    def init_timer(self):
        """初始化定时器（用于仿真数据更新）"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation_data)
        self.timer.start(1000)  # 1秒更新一次

    def toggle_serial(self):
        """切换串口连接状态"""
        if self.serial_thread and self.serial_thread.is_running:
            # 断开串口
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("连接串口")
            self.send_btn.setEnabled(False)
            self.log_text.append("串口已断开")
            self.status_bar.showMessage("串口已断开 - 仿真模式")
        else:
            # 连接串口
            try:
                port = self.port_edit.text().strip()
                baudrate = int(self.baud_edit.text().strip())
                self.serial_thread = SerialThread(port, baudrate)
                self.serial_thread.recv_signal.connect(self.on_serial_recv)
                self.serial_thread.error_signal.connect(self.on_serial_error)
                self.serial_thread.start()
                self.connect_btn.setText("断开串口")
                self.send_btn.setEnabled(True)
                self.status_bar.showMessage(f"串口已连接：{port} - 仿真模式")
            except ValueError:
                self.log_text.append("错误：波特率必须是数字")
            except Exception as e:
                self.log_text.append(f"串口连接失败：{str(e)}")

    def send_serial_data(self):
        """发送串口数据"""
        data = self.cmd_edit.text().strip()
        if not data:
            self.log_text.append("错误：请输入要发送的指令")
            return
        if self.serial_thread and self.serial_thread.is_running:
            self.serial_thread.send_data(data)
            self.log_text.append(f"发送：{data}")
            self.cmd_edit.clear()

    def on_serial_recv(self, data: str):
        """串口数据接收回调"""
        self.log_text.append(f"接收：{data}")
        # 可在这里解析无人机指令并更新地图

    def on_serial_error(self, error: str):
        """串口错误回调"""
        self.log_text.append(f"错误：{error}")
        self.connect_btn.setText("连接串口")
        self.send_btn.setEnabled(False)
        self.status_bar.showMessage("串口错误 - 仿真模式")

    def on_map_loaded(self, success: bool):
        """地图加载完成回调"""
        if success:
            self.log_text.append("地图加载成功")
            self.status_bar.showMessage("地图加载完成 - 仿真模式")
            # 可在这里执行JavaScript代码初始化地图
            # self.web_page.runJavaScript("initMap();")
        else:
            self.log_text.append("地图加载失败")
            self.status_bar.showMessage("地图加载失败 - 仿真模式")

    def update_simulation_data(self):
        """更新仿真数据（每秒）"""
        # 示例：模拟获取无人机状态（可替换为真实API请求）
        try:
            # 模拟网络请求
            # response = requests.get("http://localhost:8080/drone/status")
            # status = response.json()
            # self.log_text.append(f"仿真数据：{status}")
            pass
        except Exception as e:
            # 忽略仿真数据更新错误
            pass

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止串口线程
        if self.serial_thread:
            self.serial_thread.stop()
        # 停止定时器
        self.timer.stop()
        event.accept()

# 程序入口
if __name__ == "__main__":
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（可选，取消注释并替换路径）
    # app.setWindowIcon(QIcon("icon.png"))
    
    # 创建主窗口
    window = MarineClusterUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())
