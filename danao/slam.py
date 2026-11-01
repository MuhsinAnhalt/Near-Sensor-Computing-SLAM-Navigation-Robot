#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import main

slam_box = {"pose": None}


def run():
    while True:
        main.lock.acquire()
        raw = None
        canny = None
        if main.data_box["raw_img_slam"] is not None:
            raw = main.data_box["raw_img_slam"].copy()
            main.data_box["raw_img_slam"] = None
        if main.data_box["canny_img"] is not None:
            canny = main.data_box["canny_img"].copy()
            main.data_box["canny_img"] = None
        main.lock.release()

        if raw is None or canny is None:
            time.sleep(0.01)
            continue

        try:
            # 假装算位姿
            slam_box["pose"] = {"x": 1.2, "y": 3.4, "theta": 0.5}
            time.sleep(0.03)
        except Exception as e:
            print("SLAM算错了:", e)