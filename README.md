# 🤖 近感计算SLAM导航机器人
(Near Sensor Computing SLAM Navigation Robot)

> **2026 全国大学生嵌入式芯片与系统设计竞赛 - AMD 具身智能赛道参赛项目**

本项目基于 AMD Kria KV260 (FPGA) 与 Ryzen AI AIPC，构建了一套异构协同的自主导航机器人。实现了从端侧感知（硬件图像预处理）、边缘端决策（NPU SLAM/避障）到底层控制（FPGA 硬实时电机驱动）的全链路闭环。

<img width="1123" height="689" alt="幻灯片1" src="https://github.com/user-attachments/assets/5c45a994-0a77-484f-944f-6658c6ada8f2" />

## 🏗 系统架构
本项目采用经典的“云-边-端”异构架构：
*   **AIPC (大脑)**：运行 XINT8 量化模型与 SLAM 算法，负责路径规划与决策。
*   **KV260 PS端 (中枢)**：负责千兆以太网 Socket 通信、AXI 总线调度、图像 DMA 搬运。
*   **KV260 PL端 (小脑/四肢)**：纯硬件实现图像灰度化（感内计算）、编码器 4 倍频解码、PWM 生成、硬件看门狗。
<img width="1280" height="720" alt="幻灯片2" src="https://github.com/user-attachments/assets/acb217bb-1d31-42c1-89bf-d22adbc2cb80" />

## 🚀 快速复现 (Quick Start)
1. **硬件连接**：请参考下图进行接线（注意共地与供电）。
   <img width="1043" height="453" alt="幻灯片3" src="https://github.com/user-attachments/assets/04fe1ed7-c290-4067-a6c2-7fbadf8d7532" />
3. **烧录固件**：将 `fpga/metrics/scrips` 下的 `.bit` 和 `.hwh` 拷贝至 KV260，并加载 PYNQ 环境，使用jupyter运行pynq.py中的脚本。
4. **运行大脑**：在 AIPC 运行 `host/app/main.py`。

## 👥 团队分工
*   **FPGA开发 (1人)**：RTL 编写、Block Design 搭建、时序优化。
*   **AI算法 (2人)**：模型量化、NPU 部署、SLAM 算法联调。
