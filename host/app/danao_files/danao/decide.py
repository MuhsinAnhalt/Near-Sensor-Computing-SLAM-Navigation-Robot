#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import main
import xint8
import slam


def run():
    while True:
        if xint8.xint8_box["feature"] is None or slam.slam_box["pose"] is None:
            time.sleep(0.01)
            continue

        pose = slam.slam_box["pose"]

        try:
            # 替换为左右轮独立控制
            if pose["x"] < 2.0:
                pwm_A = 100
                pwm_B = 100
                dir_l = 1
                dir_r = 1
            else:
                pwm_A = 0
                pwm_B = 0
                dir_l = 1
                dir_r = 1

            main.lock.acquire()
            main.data_box["cmd"] = {
                "pwm_A": pwm_A,
                "pwm_B": pwm_B,
                "dir_l": dir_l,
                "dir_r": dir_r
            }
            main.lock.release()
        except Exception as e:
            print("决策出错了:", e)
        time.sleep(0.05)