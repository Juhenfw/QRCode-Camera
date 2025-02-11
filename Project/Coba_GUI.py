#coding=utf-8
import cv2
import numpy as np
import mvsdk
import platform
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera App")
        self.camera_list = []
        self.hCamera = None
        self.pFrameBuffer = None
        self.cap = None
        self.monoCamera = False
        self.running = False

        # UI Elements
        self.label = tk.Label(root, text="Select Camera:")
        self.label.pack(pady=10)

        self.camera_select = tk.Listbox(root)
        self.camera_select.pack(pady=10)

        self.btn_start = tk.Button(root, text="Start Camera", command=self.start_camera)
        self.btn_start.pack(pady=10)

        self.btn_stop = tk.Button(root, text="Stop Camera", command=self.stop_camera, state=tk.DISABLED)
        self.btn_stop.pack(pady=10)

        self.video_frame = tk.Label(root)
        self.video_frame.pack(pady=10)

        self.enumerate_cameras()

    def enumerate_cameras(self):
        # Enumerasi Kamera
        DevList = mvsdk.CameraEnumerateDevice()
        nDev = len(DevList)
        if nDev < 1:
            messagebox.showerror("Error", "No camera was found!")
            return

        self.camera_list = DevList

        for i, DevInfo in enumerate(DevList):
            self.camera_select.insert(tk.END, "{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))

    def start_camera(self):
        # Buka kamera
        try:
            index = self.camera_select.curselection()[0]
            DevInfo = self.camera_list[index]

            self.hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
            self.cap = mvsdk.CameraGetCapability(self.hCamera)

            self.monoCamera = (self.cap.sIspCapacity.bMonoSensor != 0)

            if self.monoCamera:
                mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
            else:
                mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

            mvsdk.CameraSetTriggerMode(self.hCamera, 0)
            mvsdk.CameraSetAeState(self.hCamera, 0)
            mvsdk.CameraSetExposureTime(self.hCamera, 30 * 1000)
            mvsdk.CameraPlay(self.hCamera)

            FrameBufferSize = self.cap.sResolutionRange.iWidthMax * self.cap.sResolutionRange.iHeightMax * (1 if self.monoCamera else 3)
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

            self.running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)

            self.update_frame()

        except mvsdk.CameraException as e:
            messagebox.showerror("Error", "CameraInit Failed({}): {}".format(e.error_code, e.message))

    def stop_camera(self):
        self.running = False

        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
            mvsdk.CameraAlignFree(self.pFrameBuffer)

        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def update_frame(self):
        if not self.running:
            return

        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 200)
            mvsdk.CameraImageProcess(self.hCamera, pRawData, self.pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)

            if platform.system() == "Windows":
                mvsdk.CameraFlipFrameBuffer(self.pFrameBuffer, FrameHead, 1)

            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)

            # Convert frame to PIL format for Tkinter
            if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
                img = Image.fromarray(frame, 'L')  # Grayscale
            else:
                img = Image.fromarray(frame[..., ::-1])  # Convert BGR to RGB for Tkinter display

            imgtk = ImageTk.PhotoImage(image=img)

            self.video_frame.imgtk = imgtk
            self.video_frame.config(image=imgtk)

            self.root.after(10, self.update_frame)

        except mvsdk.CameraException as e:
            if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                messagebox.showerror("Error", "CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))

def main():
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()

main()
