#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import numpy as np
import main

slam_box = {"pose": None}

# ==================== 差速轮式里程计参数 ====================
# 位姿由 tx.py 8080 回传的编码器计数 (int16 left/right) 推算，
# 以下参数需按实际小车硬件标定。
WHEEL_RADIUS  = 0.03    # 轮半径 (m)
COUNTS_PER_REV = 1000   # 编码器每转一圈的计数
WHEEL_BASE    = 0.25    # 左右轮距 (m)

METERS_PER_COUNT = 2.0 * np.pi * WHEEL_RADIUS / COUNTS_PER_REV


def run():
    last_l = None
    last_r = None
    pose = {"x": 0.0, "y": 0.0, "theta": 0.0}

    while True:
        main.lock.acquire()
        odo = None
        if main.data_box["odo"] is not None:
            odo = main.data_box["odo"].copy()
        main.lock.release()

        if odo is None:
            time.sleep(0.01)
            continue

        enc_l = odo.get("countA", 0)
        enc_r = odo.get("countB", 0)

        if last_l is None:
            last_l, last_r = enc_l, enc_r
            continue

        # 每个控制周期左右轮编码器增量 (来自 tx.py 的 int16 计数)
        d_l = (enc_l - last_l) * METERS_PER_COUNT
        d_r = (enc_r - last_r) * METERS_PER_COUNT
        last_l, last_r = enc_l, enc_r

        # 差速运动模型
        d_center = (d_l + d_r) / 2.0
        d_theta = (d_r - d_l) / WHEEL_BASE

        pose["x"] += d_center * np.cos(pose["theta"] + d_theta / 2.0)
        pose["y"] += d_center * np.sin(pose["theta"] + d_theta / 2.0)
        pose["theta"] += d_theta

        slam_box["pose"] = dict(pose)
        time.sleep(0.01)
