from pynq import Overlay, MMIO
import threading
import socket
import struct
import time
import numpy as np

# ==================== 配置 ====================
BIT_FILE = 'FinalFire.bit'
AIPC_IP  = '192.168.2.100'
PORT_CTRL  = 8080   # 电机控制 TCP
PORT_GRAY  = 8081   # 灰度图 UDP
PORT_CANNY = 8082   # Canny 图 UDP

# AXI 地址
ADDR_MOTOR = 0xA0000000
ADDR_ENC   = 0xA0010000
ADDR_VDMA0 = 0xA0030000   # 灰度图
ADDR_VDMA1 = 0xA0050000   # Canny 图（新加的，自己分配的地址）

# 帧分辨率
FRAME_W = 1280
FRAME_H = 720

# 喂狗周期
WDT_INTERVAL = 0.05

# ==================== 加载 FPGA ====================
print("Loading FPGA...")
ol = Overlay(BIT_FILE)
print("Done!")

MOTOR = MMIO(ADDR_MOTOR, 0x10000)
ENC   = MMIO(ADDR_ENC, 0x10000)

# ==================== VDMA 实例 (摄像头采集) ====================
# 摄像头采集链路: mipi_csi2_rx_subsys -> axi_vdma(S2MM) -> DDR
# pynq 中 S2MM(stream→DDR) 用 readchannel 访问其 buffer
try:
    VDMA_GRAY = ol.axi_vdma_0
    print("VDMA_GRAY 实例就绪:", VDMA_GRAY)
except Exception as e:
    VDMA_GRAY = None
    print("获取 VDMA_GRAY 失败:", e)
try:
    VDMA_CANNY = ol.axi_vdma_1
    print("VDMA_CANNY 实例就绪:", VDMA_CANNY)
except Exception as e:
    VDMA_CANNY = None
    print("获取 VDMA_CANNY 失败:", e)

# ==================== 电机控制 ====================
def set_motor(dl, dr, dir_l, dir_r):
    """设置电机: dl/dr=0~255, dir=0后退1前进"""
    val  = (1 << 0)           # bit0: 喂狗
    val |= (dl & 0xFF) << 1    # bits[8:1]: 左PWM
    val |= (dr & 0xFF) << 9    # bits[16:9]: 右PWM
    val |= (dir_l & 1) << 17   # bit17: 左方向
    val |= (dir_r & 1) << 18   # bit18: 右方向
    MOTOR.write(0x00, val)

def read_enc():
    """读编码器: 返回(左int16, 右int16)"""
    raw = ENC.read(0x00)
    l = raw & 0xFFFF
    r = (raw >> 16) & 0xFFFF
    if l >= 32768: l -= 65536
    if r >= 32768: r -= 65536
    return l, r

def feed_wdt():
    """持续喂狗"""
    while True:
        cur = MOTOR.read(0x00)
        MOTOR.write(0x00, cur | 0x1)
        time.sleep(WDT_INTERVAL)

# ==================== 8080 控制服务端 ====================
def ctrl_server():
    """TCP 服务端: 收电机控制, 发编码器数据"""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', PORT_CTRL))
    srv.listen(1)
    print(f"[CTRL] listening on port {PORT_CTRL}")

    while True:
        conn, addr = srv.accept()
        print(f"[CTRL] connected from {addr}")
        try:
            while True:
                # 收 4 字节: duty_l, duty_r, dir_l, dir_r
                data = conn.recv(4)
                if len(data) < 4:
                    break
                dl, dr, dirl, dirr = struct.unpack('BBBB', data)
                set_motor(dl, dr, dirl, dirr)

                # 发 4 字节: enc_l(int16), enc_r(int16)
                el, er = read_enc()
                conn.sendall(struct.pack('hh', el, er))
        except Exception as e:
            print(f"[CTRL] error: {e}")
        finally:
            conn.close()
            set_motor(0, 0, 0, 0)  # 断开停车
            print("[CTRL] disconnected, motor stopped")

# ==================== 视频流线程 ====================
def video_stream(port, name, vdma):
    """UDP 视频流: 从 VDMA buffer 读真实摄像头帧, 分包发给 AIPC
    每包 = 8字节帧头(帧序号 uint32 + 帧长 uint32) + 图像数据
    帧长字段 = 整帧字节数(灰度图 1280*720 = 921600)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    frame_size = FRAME_W * FRAME_H   # 灰度图 1字节/像素
    pkt_size = 1400                  # 每 UDP 包总长(含帧头)
    hdr = struct.Struct('<II')       # 帧序号 + 帧长 (小端)
    seq = 0

    # 启动 VDMA S2MM 读通道(摄像头→DDR)。若采集已在硬件里 free-running, 失败可忽略。
    if vdma is not None:
        try:
            vdma.readchannel.start()
            buf = np.asarray(vdma.readchannel.buffer)
            print(f"[{name}] VDMA readchannel 已启动: shape={buf.shape} dtype={buf.dtype}")
        except Exception as e:
            print(f"[{name}] VDMA readchannel start 失败: {e}")

    while True:
        try:
            if vdma is not None:
                arr = np.asarray(vdma.readchannel.buffer)
                raw = arr.view(np.uint8)          # 统一按字节取像素
                if raw.size < frame_size:
                    raise RuntimeError(f"VDMA buffer 太小: {raw.size} < {frame_size}")
                frame = raw[:frame_size].reshape(FRAME_H, FRAME_W).copy()
                # 每 30 帧打印一次画面统计, 便于确认是否读到真实图
                if seq % 30 == 0:
                    print(f"[{name}] 帧{seq}: min={frame.min()} max={frame.max()} "
                          f"非零占比={np.count_nonzero(frame) / frame.size:.3f}")
            else:
                # VDMA 未就绪时兜底占位
                frame = np.zeros((FRAME_H, FRAME_W), dtype=np.uint8)

            # 分包发送: 每包 = 8字节帧头 + 最多 (pkt_size-8) 字节数据
            flat = frame.tobytes()
            for i in range(0, len(flat), pkt_size - 8):
                chunk = flat[i:i + pkt_size - 8]
                sock.sendto(hdr.pack(seq, frame_size) + chunk, (AIPC_IP, port))
            seq += 1
            time.sleep(1/30)  # 30fps
        except Exception as e:
            print(f"[{name}] error: {e}")
            time.sleep(0.1)

# ==================== 启动所有线程 ====================
threading.Thread(target=feed_wdt, daemon=True).start()
threading.Thread(target=ctrl_server, daemon=True).start()
threading.Thread(target=video_stream, args=(PORT_GRAY,  'GRAY',  VDMA_GRAY),  daemon=True).start()
threading.Thread(target=video_stream, args=(PORT_CANNY, 'CANNY', VDMA_CANNY), daemon=True).start()

print("All services started:")
print(f"  CTRL:  0.0.0.0:{PORT_CTRL} (TCP)")
print(f"  GRAY:  0.0.0.0:{PORT_GRAY} (UDP)")
print(f"  CANNY: 0.0.0.0:{PORT_CANNY} (UDP)")
