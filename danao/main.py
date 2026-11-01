#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py —— 包含所有功能的主程序（收图、发指令、算法、界面）
直接运行这个文件就行
"""
import cv2
import numpy as np
import time
import threading
import requests
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import xint8
import slam
import decide

# ================= 全局大盒子 =================
data_box = {
    "raw_img_xint8": None,  # 给xint8用的原图
    "raw_img_slam": None,  # 给slam用的原图
    "canny_img": None,  # 给slam用的边缘图
    "odo": None,  # 编码器数据
    "cmd": None  # decide算出来的指令
}

ui_box = {
    "raw_img": None,  # 给界面显示的原图
    "canny_img": None,  # 给界面显示的Canny图
    "pose": None,  # 给界面显示的位姿
    "cmd": None  # 给界面显示的控制指令
}

lock = threading.Lock()

# 小车接收指令的地址
CAR_URL = "http://192.168.2.99:8080/control"


# ================= 接收服务 =================
class MyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            port = self.server.server_port

            if port == 8081:  # 接收原图 1280x720
                arr = np.frombuffer(body, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    lock.acquire()
                    data_box["raw_img_xint8"] = img.copy()
                    data_box["raw_img_slam"] = img.copy()
                    ui_box["raw_img"] = img.copy()
                    lock.release()

            elif port == 8082:  # 接收边缘图
                arr = np.frombuffer(body, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    lock.acquire()
                    data_box["canny_img"] = img.copy()
                    ui_box["canny_img"] = img.copy()
                    lock.release()

            elif port == 8080:  # 接收编码器
                lock.acquire()
                data_box["odo"] = body
                lock.release()
        except Exception as e:
            print("接收出错了:", e)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass


def start_server(port):
    try:
        server = HTTPServer(('0.0.0.0', port), MyHandler)
        print(f"服务启动: 监听端口 {port}")
        server.serve_forever()
    except Exception as e:
        print(f"端口 {port} 启动失败: {e}")


# ================= 发指令线程 =================
def send_cmd_loop():
    while True:
        cmd_to_send = None
        lock.acquire()
        if data_box["cmd"] is not None:
            cmd_to_send = data_box["cmd"]
            data_box["cmd"] = None
        lock.release()

        if cmd_to_send is not None:
            try:
                requests.post(CAR_URL, json=cmd_to_send, timeout=0.5)
            except Exception as e:
                pass  # 网络发不出去就算了，不刷屏报错了
        time.sleep(0.05)


# ================= 同步数据给界面的线程 =================
def ui_sync_loop():
    while True:
        lock.acquire()
        if slam.slam_box["pose"] is not None:
            ui_box["pose"] = slam.slam_box["pose"].copy()
        if data_box["cmd"] is not None:
            ui_box["cmd"] = data_box["cmd"]
        lock.release()
        time.sleep(0.05)


# ================= 界面辅助函数 =================
def resize_with_padding(img, target_w, target_h):
    h, w = img.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(img, (new_w, new_h))
    padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return padded


# ================= 界面主循环（队友的代码） =================
def dashboard_loop():
    print("Dashboard 界面已启动！按 'q' 退出...")
    W, H = 1280, 720
    PANEL_W = 400
    IMG_W = 850
    IMG_H = 345

    pwm_A, pwm_B, dir_A, dir_B = 0, 0, 1, 1
    count_A, count_B = 0, 0
    status_text = "Waiting..."

    while True:
        # 安全拿数据
        lock.acquire()
        raw_img = ui_box["raw_img"].copy() if ui_box.get("raw_img") is not None else None
        canny_img = ui_box["canny_img"].copy() if ui_box.get("canny_img") is not None else None
        cmd = ui_box["cmd"].copy() if ui_box.get("cmd") is not None else None
        pose = ui_box.get("pose")
        odo_raw = data_box.get("odo")
        lock.release()

        # 解析指令
        if cmd is not None:
            pwm_A = cmd.get("pwm_A", 0)
            pwm_B = cmd.get("pwm_B", 0)
            dir_A = cmd.get("dir_A", 1)
            dir_B = cmd.get("dir_B", 1)
            status_text = "Auto Driving"

        # 解析编码器
        if odo_raw is not None:
            try:
                if isinstance(odo_raw, dict):
                    count_A = odo_raw.get("countA", 0)
                    count_B = odo_raw.get("countB", 0)
                elif isinstance(odo_raw, bytes):
                    odo_dict = json.loads(odo_raw.decode('utf-8'))
                    count_A = odo_dict.get("countA", 0)
                    count_B = odo_dict.get("countB", 0)
            except:
                pass

                # 画图
        canvas = np.ones((H, W, 3), dtype=np.uint8) * 240

        # 左边面板
        cv2.rectangle(canvas, (10, 10), (10 + PANEL_W, H - 10), (255, 255, 255), -1)
        cv2.rectangle(canvas, (10, 10), (10 + PANEL_W, H - 10), (0, 0, 0), 2)
        cv2.putText(canvas, "SYSTEM DATA", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
        cv2.line(canvas, (20, 80), (PANEL_W, 80), (0, 0, 0), 1)
        cv2.putText(canvas, f"Status: {status_text}", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)

        # 修复了位姿显示，防止超长
        if pose is not None:
            pose_str = f"X:{pose.get('x', 0):.2f} Y:{pose.get('y', 0):.2f} Th:{pose.get('theta', 0):.2f}"
            cv2.putText(canvas, f"Pose: {pose_str}", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 0), 2)

        cv2.putText(canvas, f"PWMA: {pwm_A}", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"dirA: {dir_A}", (250, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"PWMB: {pwm_B}", (30, 290), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"dirB: {dir_B}", (250, 290), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"Count A: {count_A}", (30, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 100, 200), 2)
        cv2.putText(canvas, f"Count B: {count_B}", (30, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 100, 200), 2)
        cv2.putText(canvas, "Dir: 1=Fwd 0=Bwd", (30, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        # 右上：原图
        img1_x, img1_y = PANEL_W + 20, 10
        cv2.rectangle(canvas, (img1_x, img1_y), (img1_x + IMG_W, img1_y + IMG_H), (0, 0, 0), -1)
        cv2.rectangle(canvas, (img1_x, img1_y), (img1_x + IMG_W, img1_y + IMG_H), (0, 0, 0), 2)
        cv2.putText(canvas, "IMAGE 1: Original", (img1_x + 10, img1_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)
        if raw_img is not None:
            padded_img1 = resize_with_padding(raw_img, IMG_W - 4, IMG_H - 4)
            canvas[img1_y + 2:img1_y + IMG_H - 2, img1_x + 2:img1_x + IMG_W - 2] = padded_img1
        else:
            cv2.putText(canvas, "NO SIGNAL", (img1_x + 250, img1_y + 170), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255),
                        3)

        # 右下：特征图
        img2_x, img2_y = PANEL_W + 20, 365
        cv2.rectangle(canvas, (img2_x, img2_y), (img2_x + IMG_W, img2_y + IMG_H), (0, 0, 0), -1)
        cv2.rectangle(canvas, (img2_x, img2_y), (img2_x + IMG_W, img2_y + IMG_H), (0, 0, 0), 2)
        cv2.putText(canvas, "IMAGE 2: Features", (img2_x + 10, img2_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)
        if canny_img is not None:
            if len(canny_img.shape) == 2:
                canny_bgr = cv2.cvtColor(canny_img, cv2.COLOR_GRAY2BGR)
            else:
                canny_bgr = canny_img
            padded_img2 = resize_with_padding(canny_bgr, IMG_W - 4, IMG_H - 4)
            canvas[img2_y + 2:img2_y + IMG_H - 2, img2_x + 2:img2_x + IMG_W - 2] = padded_img2
        else:
            cv2.putText(canvas, "NO FEATURE", (img2_x + 250, img2_y + 170), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255),
                        3)

        cv2.imshow("AI PC Dashboard", canvas)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()


# ================= 主入口 =================
if __name__ == "__main__":
    print("=== AIPC 启动 ===")

    threading.Thread(target=start_server, args=(8080,)).start()
    threading.Thread(target=start_server, args=(8081,)).start()
    threading.Thread(target=start_server, args=(8082,)).start()

    threading.Thread(target=send_cmd_loop).start()
    threading.Thread(target=ui_sync_loop).start()

    threading.Thread(target=xint8.run).start()
    threading.Thread(target=slam.run).start()
    threading.Thread(target=decide.run).start()

    # 启动界面（必须在主线程运行，否则 cv2.imshow 会闪退）
    dashboard_loop()

    # 按 q 退出界面后，程序结束
    print("程序退出")