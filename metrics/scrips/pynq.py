from pynq import Overlay, MMIO, allocate
import threading
import socket
import struct
import time
import numpy as np
import os

# ==================== 配置区 ====================
BIT_FILE = '2026110402.bit'   # 改成你最终用的 bit 文件名
PORT_CTRL  = 8080             # 控制指令端口
PORT_GRAY  = 8081             # 灰度图端口

ADDR_MOTOR = 0xA0000000       # 电机控制 GPIO
ADDR_ENC   = 0xA0010000       # 编码器输入 GPIO
ADDR_VDMA0 = 0xA0030000       # VDMA0（灰度图 S2MM）
ADDR_I2C_GPIO = 0xA0070000    # 软件 I2C 用的 GPIO
SDA_PIN = 0
SCL_PIN = 1

FRAME_W = 1280
FRAME_H = 720
WDT_INTERVAL = 0.05
IMX219_ADDR = 0x10

# ==================== 软件 I2C ====================
I2C_GPIO = MMIO(ADDR_I2C_GPIO, 0x10000)

def i2c_delay():
    time.sleep(0.0001)

def sda_out_high():
    val = I2C_GPIO.read(0x04)
    I2C_GPIO.write(0x04, val | (1 << SDA_PIN))

def sda_out_low():
    val = I2C_GPIO.read(0x04)
    I2C_GPIO.write(0x04, val & ~(1 << SDA_PIN))
    val = I2C_GPIO.read(0x00)
    I2C_GPIO.write(0x00, val & ~(1 << SDA_PIN))

def scl_out_high():
    val = I2C_GPIO.read(0x04)
    I2C_GPIO.write(0x04, val | (1 << SCL_PIN))

def scl_out_low():
    val = I2C_GPIO.read(0x04)
    I2C_GPIO.write(0x04, val & ~(1 << SCL_PIN))
    val = I2C_GPIO.read(0x00)
    I2C_GPIO.write(0x00, val & ~(1 << SCL_PIN))

def read_sda():
    val = I2C_GPIO.read(0x00)
    return (val >> SDA_PIN) & 1

def i2c_start():
    sda_out_high()
    scl_out_high()
    i2c_delay()
    sda_out_low()
    i2c_delay()
    scl_out_low()
    i2c_delay()

def i2c_stop():
    sda_out_low()
    i2c_delay()
    scl_out_high()
    i2c_delay()
    sda_out_high()
    i2c_delay()

def i2c_write_byte(data):
    for i in range(8):
        if data & 0x80:
            sda_out_high()
        else:
            sda_out_low()
        i2c_delay()
        scl_out_high()
        i2c_delay()
        scl_out_low()
        i2c_delay()
        data <<= 1
    sda_out_high()
    i2c_delay()
    scl_out_high()
    i2c_delay()
    ack = read_sda()
    scl_out_low()
    i2c_delay()
    return ack == 0

def imx219_write_reg(reg, val):
    i2c_start()
    i2c_write_byte(IMX219_ADDR << 1)
    i2c_write_byte((reg >> 8) & 0xFF)
    i2c_write_byte(reg & 0xFF)
    i2c_write_byte(val)
    i2c_stop()
    time.sleep(0.001)

# ==================== 手动配置 VDMA ====================
def config_vdma(vdma_addr, fb_addr, hsize, vsize):
    vdma = MMIO(vdma_addr, 0x1000)
    vdma.write(0x30, 0x00)
    time.sleep(0.1)
    vdma.write(0xAC, fb_addr)
    vdma.write(0xA4, hsize)
    vdma.write(0xA0, vsize)
    vdma.write(0xA8, hsize)
    vdma.write(0x30, 0x01)
    print(f"✅ VDMA @ {hex(vdma_addr)} 配置完成")

# ==================== 1. 加载 FPGA ====================
print(f"[1/5] 加载 FPGA 比特流: {BIT_FILE} ...")
ol = Overlay(BIT_FILE)
print("✅ FPGA 加载成功!")

MOTOR = MMIO(ADDR_MOTOR, 0x10000)
ENC   = MMIO(ADDR_ENC, 0x10000)

# ==================== 2. 分配帧缓冲区 ====================
print(f"\n[2/5] 分配帧缓冲区 ({FRAME_W}x{FRAME_H}) ...")
fb_gray = allocate(shape=(FRAME_H, FRAME_W), dtype=np.uint8)
print(f"✅ 帧缓冲区分配成功, 物理地址: {hex(fb_gray.physical_address)}")

# ==================== 3. 摄像头上电 + 初始化 ====================
print("\n[3/5] 摄像头上电 + IMX219 初始化 ...")
os.system("echo 412 | sudo tee /sys/class/gpio/export 2>/dev/null")
os.system("echo out | sudo tee /sys/class/gpio/gpio412/direction")
os.system("echo 1 | sudo tee /sys/class/gpio/gpio412/value")
time.sleep(0.5)

imx219_write_reg(0x3000, 0x01)
time.sleep(0.01)
imx219_write_reg(0x0100, 0x01)
time.sleep(0.1)

config_regs = [
    (0x0300, 0x05), (0x0301, 0x00), (0x0302, 0x02), (0x0303, 0x00),
    (0x0304, 0x04), (0x0305, 0x00), (0x0306, 0x00), (0x0307, 0x02),
    (0x030b, 0x01), (0x030c, 0x0a), (0x030e, 0x04), (0x0340, 0x00),
    (0x0341, 0x1f), (0x0342, 0x00), (0x0343, 0x11), (0x0344, 0x00),
    (0x0345, 0x00), (0x0309, 0x12), (0x0200, 0x00), (0x0201, 0x00),
    (0x0202, 0x00), (0x0203, 0x00), (0x0348, 0x75), (0x0349, 0x30),
    (0x034a, 0x2c), (0x034b, 0xa0), (0x0244, 0x00), (0x0245, 0x1e),
    (0x0246, 0x00), (0x0247, 0x1e), (0x0204, 0x00), (0x0205, 0x00),
]

for reg, val in config_regs:
    imx219_write_reg(0x3000, 0x01)
    imx219_write_reg(reg, val)
    time.sleep(0.001)

print("✅ IMX219 初始化完成")
time.sleep(1)

# 配置 VDMA
config_vdma(ADDR_VDMA0, fb_gray.physical_address, FRAME_W, FRAME_H)

time.sleep(1)
vdma0 = MMIO(ADDR_VDMA0, 0x1000)
print(f"VDMA0 帧计数: {hex(vdma0.read(0x34))}")
print(f"帧缓冲区最大值: {fb_gray.max()}")

# ==================== 4. 电机控制函数 ====================
print("\n[4/5] 初始化电机控制 ...")

def set_motor(dl, dr, dir_l, dir_r):
    val  = (1 << 0) | (dl << 1) | (dr << 9) | (dir_l << 17) | (dir_r << 18)
    MOTOR.write(0x00, val)

def read_enc():
    raw = ENC.read(0x00)
    l = raw & 0xFFFF
    r = (raw >> 16) & 0xFFFF
    if l >= 32768: l -= 65536
    if r >= 32768: r -= 65536
    return l, r

def feed_wdt():
    while True:
        cur = MOTOR.read(0x00)
        MOTOR.write(0x00, cur | 0x1)
        time.sleep(WDT_INTERVAL)

print("✅ 电机控制初始化完成")

# ==================== 5. TCP 通信服务 ====================
print("\n[5/5] 启动 TCP 通信服务 ...")

def recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk: raise ConnectionError("断开")
        buf += chunk
    return buf

def ctrl_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', PORT_CTRL))
    srv.listen(1)
    print(f"✅ 控制服务监听: {PORT_CTRL}")

    while True:
        conn, addr = srv.accept()
        print(f"🎉 AIPC 已连接 (控制通道)")
        try:
            while True:
                data = recv_exact(conn, 4)
                dl, dr, dirl, dirr = struct.unpack('BBBB', data)
                set_motor(dl, dr, dirl, dirr)
                el, er = read_enc()
                conn.sendall(struct.pack('hh', el, er))
        except Exception as e:
            print(f"[控制通道] 断开: {e}")
        finally:
            conn.close()
            set_motor(0, 0, 0, 0)
            print("[控制通道] 已安全停车，等待重连...")

def tcp_video_server(port, name, fb_array):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', port))
    srv.listen(1)
    print(f"✅ {name} 视频服务监听: {port}")

    while True:
        conn, addr = srv.accept()
        print(f"🎥 AIPC 已连接 ({name} 通道)")
        try:
            while True:
                frame = fb_array.copy()
                flat = frame.tobytes()
                conn.sendall(struct.pack('<I', len(flat)))
                conn.sendall(flat)
                time.sleep(1/30)
        except Exception as e:
            print(f"[{name} 通道] 断开: {e}")
        finally:
            conn.close()

# ==================== 启动 ====================
if __name__ == "__main__":
    threading.Thread(target=feed_wdt, daemon=True).start()
    threading.Thread(target=ctrl_server, daemon=True).start()
    threading.Thread(target=tcp_video_server, args=(PORT_GRAY, 'GRAY', fb_gray), daemon=True).start()

    print("\n" + "="*40)
    print("✅ KV260 系统全部启动完成!")
    print("="*40)
    print(f"  控制端口: {PORT_CTRL}")
    print(f"  灰度图端口: {PORT_GRAY}")
    print(f"  小车 IP: 192.168.2.99")
    print("="*40 + "\n")

    while True:
        time.sleep(1)
