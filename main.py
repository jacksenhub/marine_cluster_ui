import sys
import json
import math
import random
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QFont

class FleetSimulationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("海洋航行器水池定位可视化系统")
        self.setGeometry(100, 100, 1600, 1000)

        # 水池配置
        self.pool_config = {
            "width": 50.0,
            "length": 30.0,
            "origin_x": 0.0,
            "origin_y": 0.0
        }

        # 集群数据
        self.fleet_data = {
            "leader": {
                "id": "L01", "x": 25.0, "y": 15.0,
                "role": "指挥船", "speed": 0.0, "heading": 0.0, "battery": 100.0
            },
            "followers": [
                {"id": "F01", "x": 20.0, "y": 10.0, "offset_x": -5.0, "offset_y": -5.0, "battery": 98.0, "motor_rpm": 0, "status": "正常"},
                {"id": "F02", "x": 20.0, "y": 20.0, "offset_x": -5.0, "offset_y": 5.0, "battery": 95.0, "motor_rpm": 0, "status": "正常"},
                {"id": "F03", "x": 30.0, "y": 15.0, "offset_x": 5.0, "offset_y": 0.0, "battery": 92.0, "motor_rpm": 0, "status": "正常"}
            ]
        }

        self.trajectories = {"leader": [], "followers": [[], [], []]}
        self.max_trajectory_points = 500
        self.water_current = {"speed": 0.0, "direction": 0.0}
        self.comm_delay = 50
        self.simulation_active = True
        self.update_interval = 100

        self.init_ui()

        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_simulation_loop)
        self.sim_timer.start(self.update_interval)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪 - 仿真运行中")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 左侧面板
        left_panel = QGroupBox("🎛️ 集群控制中心")
        left_panel.setMinimumWidth(320)
        left_layout = QVBoxLayout()

        # 水池参数 + 应用按钮
        pool_group = QGroupBox("🏊 水池参数")
        pool_form = QFormLayout()
        self.pool_width_input = QLineEdit(str(self.pool_config["width"]))
        self.pool_length_input = QLineEdit(str(self.pool_config["length"]))
        self.pool_apply_btn = QPushButton("应用水池尺寸")
        self.pool_apply_btn.clicked.connect(self.apply_pool_config)
        self.pool_apply_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        pool_form.addRow("水池宽度 (米):", self.pool_width_input)
        pool_form.addRow("水池长度 (米):", self.pool_length_input)
        pool_form.addRow("", self.pool_apply_btn)
        pool_group.setLayout(pool_form)

        # 通信配置
        serial_group = QGroupBox("📡 通信配置")
        serial_form = QFormLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM3", "COM4", "COM5", "/dev/ttyUSB0"])
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "57600", "256000"])
        serial_form.addRow("串口端口:", self.port_combo)
        serial_form.addRow("波特率:", self.baud_combo)
        serial_group.setLayout(serial_form)

        # 指令
        cmd_group = QGroupBox("📤 指令发送")
        cmd_layout = QVBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("指令: start, stop, formation...")
        self.cmd_input.returnPressed.connect(self.send_command)
        self.send_btn = QPushButton("发送指令")
        self.send_btn.clicked.connect(self.send_command)
        self.send_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        cmd_layout.addWidget(self.cmd_input)
        cmd_layout.addWidget(self.send_btn)
        cmd_group.setLayout(cmd_layout)

        # 干扰
        disturb_group = QGroupBox("⚠️ 环境干扰注入")
        disturb_layout = QVBoxLayout()
        self.water_btn = QPushButton("💧 注入突发水流")
        self.delay_btn = QPushButton("📡 模拟通信延迟")
        self.collision_btn = QPushButton("🔧 模拟船舶故障")
        self.reset_btn = QPushButton("🔄 重置所有干扰")
        self.reset_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.water_btn.clicked.connect(self.inject_water)
        self.delay_btn.clicked.connect(self.inject_delay)
        self.collision_btn.clicked.connect(self.inject_fault)
        self.reset_btn.clicked.connect(self.reset_all)
        disturb_layout.addWidget(self.water_btn)
        disturb_layout.addWidget(self.delay_btn)
        disturb_layout.addWidget(self.collision_btn)
        disturb_layout.addWidget(self.reset_btn)
        disturb_group.setLayout(disturb_layout)

        # 状态
        status_group = QGroupBox("📊 实时状态")
        status_layout = QVBoxLayout()
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QFont("Consolas", 9))
        self.status_text.setMaximumHeight(150)
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)

        # 日志
        log_group = QGroupBox("📝 系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 8))
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)

        left_layout.addWidget(pool_group)
        left_layout.addWidget(serial_group)
        left_layout.addWidget(cmd_group)
        left_layout.addWidget(disturb_group)
        left_layout.addWidget(status_group)
        left_layout.addWidget(log_group)
        left_panel.setLayout(left_layout)

        # 地图
        self.map_view = QWebEngineView()
        self.create_and_load_map_html()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

        self.log_message("✅ 系统启动 - 水池定位可视化系统已激活")
        self.log_message(f"🏊 水池尺寸: {self.pool_config['width']}m × {self.pool_config['length']}m")
        self.log_message("🚤 集群初始化: 1 指挥船 + 3 跟随船")
        self.update_status_display()

    def apply_pool_config(self):
        try:
            new_width = float(self.pool_width_input.text())
            new_length = float(self.pool_length_input.text())
            if new_width <= 0 or new_length <= 0:
                self.log_message("❌ 水池尺寸必须>0！")
                return
            self.pool_config["width"] = new_width
            self.pool_config["length"] = new_length
            cx = new_width/2
            cy = new_length/2
            self.fleet_data["leader"]["x"] = cx
            self.fleet_data["leader"]["y"] = cy
            for i, f in enumerate(self.fleet_data["followers"]):
                f["x"] = cx + f["offset_x"]
                f["y"] = cy + f["offset_y"]
            self.trajectories = {"leader": [], "followers": [[], [], []]}
            self.create_and_load_map_html()
            self.log_message(f"✅ 水池已更新: {new_width}×{new_length}m")
        except ValueError:
            self.log_message("❌ 请输入有效数字！")
            self.pool_width_input.setText(str(self.pool_config["width"]))
            self.pool_length_input.setText(str(self.pool_config["length"]))

    def create_and_load_map_html(self):
        # 核心修复：使用平面坐标系，完全适配米制局部坐标
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>
        body,html{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#1a1a2e;}}
        #map{{width:100%;height:100%;}}
        #panel{{position:absolute;top:10px;right:10px;background:#0008;color:#fff;padding:8px 12px;border-radius:6px;font-size:12px;}}
        #legend{{position:absolute;bottom:10px;right:10px;background:#fff;padding:8px;border-radius:6px;font-size:11px;}}
        .leg{{display:flex;align-items:center;margin:3px 0;}}
        .col{{width:10px;height:10px;border-radius:50%;margin-right:6px;}}
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v7.3.0/ol.css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v7.3.0/dist/ol.js"></script>
</head>
<body>
<div id="map"></div>
<div id="panel">指挥船: <span id="pos">0,0</span></div>
<div id="legend">
    <div class="leg"><div class="col" style="background:#FFD700"></div>指挥船</div>
    <div class="leg"><div class="col" style="background:#00BFFF"></div>跟随船</div>
    <div class="leg"><div class="col" style="background:#FF4500"></div>编队线</div>
</div>

<script>
    const W = {self.pool_config['width']};
    const H = {self.pool_config['length']};

    // 自定义平面投影（关键修复！）
    const proj = new ol.proj.Projection({
        code: 'POOL',
        units: 'm',
    });

    const map = new ol.Map({{
        target: 'map',
        layers: [
            new ol.layer.Vector({{
                source: new ol.source.Vector(),
                style: new ol.style.Style({{
                    stroke: new ol.style.Stroke({{color: '#fff', width:2}}),
                    fill: new ol.style.Fill({{color: 'rgba(100,149,237,0.2)'}})
                }})
            }})
        ],
        view: new ol.View({{
            projection: proj,
            center: [W/2, H/2],
            zoom: 1.2,
            minZoom: 1,
            maxZoom: 5,
            extent: [0,0,W,H]
        }})
    }});

    // 图层
    const srcPool = new ol.source.Vector();
    const srcShip = new ol.source.Vector();
    const srcLine = new ol.source.Vector();
    const srcTraj = new ol.source.Vector();

    map.addLayer(new ol.layer.Vector({{source:srcPool}}));
    map.addLayer(new ol.layer.Vector({{source:srcLine}}));
    map.addLayer(new ol.layer.Vector({{source:srcTraj, style: new ol.style.Style({{
        stroke: new ol.style.Stroke({{color:'rgba(255,255,255,0.3)', width:2}})
    }})}}));
    map.addLayer(new ol.layer.Vector({{source:srcShip}}));

    // 画水池
    srcPool.addFeature(new ol.Feature({{
        geometry: new ol.geom.Polygon([[[0,0],[W,0],[W,H],[0,H],[0,0]]])
    }}));

    let leader = null;
    let followers = [];

    function updateMap(data) {{
        srcShip.clear();
        srcLine.clear();
        srcTraj.clear();

        // 指挥船
        const lx = data.leader.x;
        const ly = data.leader.y;
        document.getElementById('pos').textContent = lx.toFixed(1)+', '+ly.toFixed(1);

        const lfeat = new ol.Feature({{geometry: new ol.geom.Point([lx, ly])}});
        lfeat.setStyle(new ol.style.Style({{
            image: new ol.style.Circle({{radius:14, fill:new ol.style.Fill({{color:'#FFD700'}}), stroke:new ol.style.Stroke({{color:'#fff', width:3}})}}),
            text: new ol.style.Text({{text:data.leader.id, offsetY:-20, font:'bold 12px Arial', fill:new ol.style.Fill({{color:'#FFD700'}})}})
        }}));
        srcShip.addFeature(lfeat);

        // 跟随船 & 连线
        data.followers.forEach((f, i) => {{
            const fx = f.x;
            const fy = f.y;
            const ffeat = new ol.Feature({{geometry: new ol.geom.Point([fx, fy])}});
            ffeat.setStyle(new ol.style.Style({{
                image: new ol.style.Circle({{radius:10, fill:new ol.style.Fill({{color:'#00BFFF'}}), stroke:new ol.style.Stroke({{color:'#fff', width:2}})}}),
                text: new ol.style.Text({{text:f.id, offsetY:16, font:'bold 11px Arial', fill:new ol.style.Fill({{color:'#00BFFF'}})}})
            }}));
            srcShip.addFeature(ffeat);

            // 编队连线
            const line = new ol.Feature({{geometry: new ol.geom.LineString([[lx,ly],[fx,fy]])}});
            line.setStyle(new ol.style.Style({{
                stroke: new ol.style.Stroke({{color:'#FF4500', width:2, lineDash:[5,5]}})
            }}));
            srcLine.addFeature(line);
        }});

        // 轨迹
        if(data.trajectories.leader.length>1){{
            srcTraj.addFeature(new ol.Feature({{
                geometry: new ol.geom.LineString(data.trajectories.leader)
            }}));
        }}
        data.trajectories.followers.forEach(t=>{{
            if(t.length>1) srcTraj.addFeature(new ol.Feature({{geometry: new ol.geom.LineString(t)}}));
        }});
    }}
</script>
</body>
</html>
        """
        self.map_view.setHtml(html, QUrl("file:///"))

    def update_map_view_js(self):
        data = {
            "leader": self.fleet_data["leader"],
            "followers": self.fleet_data["followers"],
            "trajectories": self.trajectories
        }
        js = f"updateMap({json.dumps(data)});"
        self.map_view.page().runJavaScript(js)

    def update_simulation_loop(self):
        if not self.simulation_active: return
        leader = self.fleet_data["leader"]

        # 指挥船圆周运动
        leader["speed"] = 0.5 + random.uniform(-0.1,0.1)
        leader["heading"] = (leader["heading"] + 0.5) % 360
        cx = self.pool_config["width"]/2
        cy = self.pool_config["length"]/2
        r = min(self.pool_config["width"], self.pool_config["length"])*0.3
        angle = math.radians(leader["heading"])
        tx = cx + r*math.cos(angle)
        ty = cy + r*math.sin(angle)
        leader["x"] = leader["x"]*0.85 + tx*0.15
        leader["y"] = leader["y"]*0.85 + ty*0.15
        leader["x"] = max(2, min(self.pool_config["width"]-2, leader["x"]))
        leader["y"] = max(2, min(self.pool_config["length"]-2, leader["y"]))

        self.trajectories["leader"].append([leader["x"], leader["y"]])
        if len(self.trajectories["leader"]) > self.max_trajectory_points:
            self.trajectories["leader"].pop(0)

        # 跟随船
        for i, f in enumerate(self.fleet_data["followers"]):
            tx = leader["x"] + f["offset_x"]
            ty = leader["y"] + f["offset_y"]
            if self.water_current["speed"]>0:
                dx = self.water_current["speed"]*0.1*math.cos(math.radians(self.water_current["direction"]))
                dy = self.water_current["speed"]*0.1*math.sin(math.radians(self.water_current["direction"]))
                tx += dx
                ty += dy
            f["x"] = f["x"]*0.8 + tx*0.2
            f["y"] = f["y"]*0.8 + ty*0.2
            f["x"] = max(1, min(self.pool_config["width"]-1, f["x"]))
            f["y"] = max(1, min(self.pool_config["length"]-1, f["y"]))
            f["motor_rpm"] = int(1200 + abs(tx-f["x"])*100 + random.randint(-50,50))
            f["battery"] = max(0, f["battery"]-0.005)
            self.trajectories["followers"][i].append([f["x"], f["y"]])
            if len(self.trajectories["followers"][i])>self.max_trajectory_points:
                self.trajectories["followers"][i].pop(0)

        self.update_map_view_js()
        if self.sim_timer.timerId() % 10 == 0:
            self.update_status_display()

    def update_status_display(self):
        l = self.fleet_data["leader"]
        s = f"🚤 指挥船 {l['id']}  ({l['x']:.1f},{l['y']:.1f})m  电量:{l['battery']:.1f}%\n\n"
        for f in self.fleet_data["followers"]:
            s += f"🚤 {f['id']}  ({f['x']:.1f},{f['y']:.1f})m  电量:{f['battery']:.1f}%  RPM:{f['motor_rpm']}\n"
        s += f"\n💧水流:{self.water_current['speed']:.1f}m/s  📡延迟:{self.comm_delay}ms"
        self.status_text.setText(s)

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if cmd:
            self.log_message(f"📤 发送指令: {cmd}")
            self.cmd_input.clear()

    def inject_water(self):
        self.water_current["speed"] = random.uniform(0.5,1.5)
        self.water_current["direction"] = random.uniform(0,360)
        self.log_message(f"💧 水流注入: {self.water_current['speed']:.1f}m/s")

    def inject_delay(self):
        self.comm_delay = random.randint(100,500)
        self.log_message(f"📡 延迟: {self.comm_delay}ms")

    def inject_fault(self):
        idx = random.randint(0,2)
        self.fleet_data["followers"][idx]["status"] = "故障"
        self.fleet_data["followers"][idx]["motor_rpm"] = 0
        self.log_message(f"⚠️ {self.fleet_data['followers'][idx]['id']} 故障")

    def reset_all(self):
        self.water_current = {"speed":0,"direction":0}
        self.comm_delay = 50
        for f in self.fleet_data["followers"]:
            f["status"] = "正常"
            f["battery"] = 95+random.uniform(0,5)
        self.trajectories = {"leader":[],"followers":[[],[],[]]}
        self.log_message("🔄 系统已重置")

    def log_message(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {msg}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def closeEvent(self, e):
        self.simulation_active = False
        self.sim_timer.stop()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = FleetSimulationWindow()
    win.show()
    sys.exit(app.exec_())
