# ================= 全局大盒子 =================
import threading
import socket
import struct
import time
import numpy as np
import cv2
import slam
import xint8
import decide

# ==================== 与 tx.py 对齐的通信配置 ====================
KV260_IP = "192.168.2.99"   # tx.py 中小车(FPGA) IP
PORT_CTRL  = 8080            # TCP 控制端口：发 PWM/dir(4B)，收编码器(4B)
PORT_GRAY  = 8081            # UDP 灰度原图帧流
PORT_CANNY = 8082            # UDP Canny 特征图帧流
FRAME_W = 1280
FRAME_H = 720
FRAME_BYTES = FRAME_W * FRAME_H   # 灰度图 = 1 字节/像素

data_box = {
    "raw_img_xint8": None,  # 给xint8用的原图(灰度)
    "raw_img_slam": None,   # 给slam用的原图(灰度)
    "canny_img": None,      # 给slam用的边缘图(灰度)
    "odo": None,            # 编码器数据 {"countA","countB"}
    "cmd": None             # decide算出来的指令
}

ui_box = {
    "raw_img": None,        # 给界面显示的原图(BGR)
    "canny_img": None,      # 给界面显示的Canny图(灰度)
    "pose": None,           # 给界面显示的位姿
    "cmd": None             # 给界面显示的控制指令
}

lock = threading.Lock()


# ================= 控制连接: 发指令 + 收编码器 =================
def recv_exact(sock, n):
    """TCP 循环接收，确保收满 n 字节"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接断开")
        buf += chunk
    return buf


def ctrl_loop():
    """连接 KV260 的 8080 TCP 控制端口（与 tx.py ctrl_server 对应）：
    发送 4 字节 struct.pack("BBBB", duty_l, duty_r, dir_l, dir_r)
    回传 4 字节 struct.pack("hh", left, right) 编码器计数
    """
    while True:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((KV260_IP, PORT_CTRL))
            print(f"[CTRL] 已连接 {KV260_IP}:{PORT_CTRL}")

            # 持续发送的当前指令(无新指令时保持上次值)，保证每个周期都能收到编码器回传
            cur = {"pwm_A": 0, "pwm_B": 0, "dir_l": 1, "dir_r": 1}
            while True:
                lock.acquire()
                if data_box["cmd"] is not None:
                    cur = data_box["cmd"]
                    data_box["cmd"] = None
                lock.release()

                # 每个周期都发送 4 字节指令，并接收 4 字节编码器回传
                pkt = struct.pack("BBBB",
                                  int(cur["pwm_A"]), int(cur["pwm_B"]),
                                  int(cur["dir_l"]), int(cur["dir_r"]))
                sock.sendall(pkt)
                enc = recv_exact(sock, 4)
                enc_l, enc_r = struct.unpack("hh", enc)
                lock.acquire()
                data_box["odo"] = {"countA": enc_l, "countB": enc_r}
                lock.release()

                time.sleep(0.05)
        except Exception as e:
            print(f"[CTRL] 连接异常: {e}")
            time.sleep(1.0)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass


# ================= UDP 图像接收 =================
# tx.py 的 video_stream 把整帧按每包 1400 字节发送，
# 每包带 8 字节帧头：帧序号(uint32) + 帧长(uint32)，后面是图像数据。
# 帧长字段 = 整帧字节数(灰度图 1280*720 = 921600)，收集满即组成一帧灰度图。
FRAME_HEADER = 8   # 帧序号 4B + 帧长 4B

def recv_udp_frame(port, name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    print(f"[{name}] UDP 监听端口 {port}")
    buf = bytearray()
    last_seq = None
    while True:
        try:
            data, _ = sock.recvfrom(65536)
            if len(data) < FRAME_HEADER:
                continue
            # 解析帧头 (小端，与 tx.py 默认字节序一致)
            seq, frame_len = struct.unpack("<II", data[:FRAME_HEADER])
            payload = data[FRAME_HEADER:]

            # 帧序号变化 => 新一帧开始，丢弃上一帧残留（丢包自愈）
            if last_seq is not None and seq != last_seq:
                buf = bytearray()
            last_seq = seq

            # 帧长合理性保护，防止异常值撑爆 buffer
            if frame_len <= 0 or frame_len > FRAME_BYTES * 2:
                continue

            buf += payload
            if len(buf) >= frame_len:
                frame = np.frombuffer(bytes(buf[:frame_len]), dtype=np.uint8)
                del buf[:frame_len]
                yield frame.reshape((FRAME_H, FRAME_W))
        except Exception as e:
            print(f"[{name}] 接收错误: {e}")


def recv_gray_loop():
    """8081 灰度原图"""
    for img in recv_udp_frame(PORT_GRAY, "GRAY"):
        lock.acquire()
        data_box["raw_img_xint8"] = img.copy()
        data_box["raw_img_slam"] = img.copy()
        ui_box["raw_img"] = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        lock.release()


def recv_canny_loop():
    """8082 Canny 特征图"""
    for img in recv_udp_frame(PORT_CANNY, "CANNY"):
        lock.acquire()
        data_box["canny_img"] = img.copy()
        ui_box["canny_img"] = img.copy()
        lock.release()


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

    pwm_A, pwm_B, dir_l, dir_r = 0, 0, 1, 1
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
            dir_l = cmd.get("dir_l", 1)
            dir_r = cmd.get("dir_r", 1)
            status_text = "Auto Driving"

        # 解析编码器 (来自 tx.py 8080 回传的 int16 计数)
        if odo_raw is not None:
            try:
                count_A = odo_raw.get("countA", 0)
                count_B = odo_raw.get("countB", 0)
            except Exception:
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
        cv2.putText(canvas, f"dirA: {dir_l}", (250, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"PWMB: {pwm_B}", (30, 290), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
        cv2.putText(canvas, f"dirB: {dir_r}", (250, 290), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 0), 2)
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

    # 与 tx.py 通信
    threading.Thread(target=ctrl_loop, daemon=True).start()
    threading.Thread(target=recv_gray_loop, daemon=True).start()
    threading.Thread(target=recv_canny_loop, daemon=True).start()

    # 内部处理与界面
    threading.Thread(target=ui_sync_loop).start()
    threading.Thread(target=xint8.run).start()
    threading.Thread(target=slam.run).start()
    threading.Thread(target=decide.run).start()

    # 启动界面（必须在主线程运行，否则 cv2.imshow 会闪退）
    dashboard_loop()

    # 按 q 退出界面后，程序结束
    print("程序退出")
