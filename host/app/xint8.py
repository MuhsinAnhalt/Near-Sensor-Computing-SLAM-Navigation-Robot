#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import time
import onnxruntime as ort
import main

xint8_box = {"feature": None}

try:
    session = ort.InferenceSession("model_xint8.onnx", providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    print("模型加载成功")
except Exception as e:
    print("模型加载失败:", e)
    session = None


def run():
    while True:
        if session is None:
            time.sleep(1)
            continue

        main.lock.acquire()
        img = None
        if main.data_box["raw_img_xint8"] is not None:
            img = main.data_box["raw_img_xint8"].copy()
            main.data_box["raw_img_xint8"] = None
        main.lock.release()

        if img is None:
            time.sleep(0.01)
            continue

        try:
            img_resized = cv2.resize(img, (640, 640))
            # tx.py 的 8081 发来的是 1280x720 灰度原图，先补成 3 通道再进网络
            if len(img_resized.shape) == 2:
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_GRAY2RGB)
            else:
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            img_float = img_rgb.astype(np.float32) / 255.0
            img_input = img_float.transpose(2, 0, 1)
            img_input = np.expand_dims(img_input, axis=0)

            output = session.run(None, {input_name: img_input})
            xint8_box["feature"] = output[0]
        except Exception as e:
            print("模型算错了:", e)