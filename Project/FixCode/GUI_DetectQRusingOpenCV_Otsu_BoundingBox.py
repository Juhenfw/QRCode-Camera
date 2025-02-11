import cv2
import numpy as np
import mvsdk
import time
import platform
import threading
import tkinter as tk
from tkinter import ttk, messagebox

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Code Detector with Camera Control")
        self.root.geometry("900x700")

        self.hCamera = None
        self.frame_count = 0
        self.last_qr_print_time = 0
        self.qr_print_interval = 0.5

        self.qr_code_text = tk.StringVar()  # Untuk menampilkan output QR Code di GUI
        self.running = False
        self.stop_event = threading.Event()  # For thread management

        self.init_camera()
        self.build_gui()

    def init_camera(self):
        DevList = mvsdk.CameraEnumerateDevice()
        if len(DevList) < 1:
            messagebox.showerror("Error", "No camera was found!")
            self.root.quit()
            return

        DevInfo = DevList[0]
        self.hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
        cap = mvsdk.CameraGetCapability(self.hCamera)

        modeMono = (cap.sIspCapacity.bMonoSensor != 0)
        if modeMono:
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
        else:
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

        mvsdk.CameraSetTriggerMode(self.hCamera, 0)
        mvsdk.CameraSetAeState(self.hCamera, 0)
        mvsdk.CameraSetExposureTime(self.hCamera, 23 * 1000)
        mvsdk.CameraPlay(self.hCamera)

        self.pFrameBuffer = mvsdk.CameraAlignMalloc(
            cap.sResolutionRange.iWidthMax * 
            cap.sResolutionRange.iHeightMax * (1 if modeMono else 3), 16
        )

    def build_gui(self):
        # Frame Video
        self.video_label = tk.Label(self.root)
        self.video_label.pack()

        # Frame untuk Kontrol dan Output QR Code
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=10)

        # Slider dan Nilai Exposure
        tk.Label(controls_frame, text="Exposure Time (ms):").grid(row=0, column=0)
        self.exposure_value = tk.Label(controls_frame, text="23000")  # Default nilai
        self.exposure_value.grid(row=0, column=2)
        self.exposure_slider = ttk.Scale(
            controls_frame, from_=4.5, to=584358, orient=tk.HORIZONTAL, 
            command=lambda val: self.update_slider_value(val, "exposure")
        )
        self.exposure_slider.set(23000)
        self.exposure_slider.grid(row=0, column=1)

        # Slider dan Nilai Gamma
        tk.Label(controls_frame, text="Gamma:").grid(row=1, column=0)
        self.gamma_value = tk.Label(controls_frame, text="60")  # Default nilai
        self.gamma_value.grid(row=1, column=2)
        self.gamma_slider = ttk.Scale(
            controls_frame, from_=0, to=250, orient=tk.HORIZONTAL, 
            command=lambda val: self.update_slider_value(val, "gamma")
        )
        self.gamma_slider.set(60)
        self.gamma_slider.grid(row=1, column=1)

        # Slider dan Nilai Contrast
        tk.Label(controls_frame, text="Contrast:").grid(row=2, column=0)
        self.contrast_value = tk.Label(controls_frame, text="200")  # Default nilai
        self.contrast_value.grid(row=2, column=2)
        self.contrast_slider = ttk.Scale(
            controls_frame, from_=0, to=200, orient=tk.HORIZONTAL, 
            command=lambda val: self.update_slider_value(val, "contrast")
        )
        self.contrast_slider.set(200)
        self.contrast_slider.grid(row=2, column=1)

        # Tombol Start dan Stop
        self.start_button = tk.Button(self.root, text="Start", command=self.start_stream)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_stream)
        self.stop_button.pack(pady=5)

        # Label Output QR Code
        tk.Label(self.root, text="QR Code Output:").pack(pady=5)
        self.qr_output_label = tk.Label(self.root, textvariable=self.qr_code_text, font=("Arial", 14))
        self.qr_output_label.pack()

        # Tombol Keluar
        self.exit_button = tk.Button(self.root, text="Exit", command=self.close_app, bg="red", fg="white")
        self.exit_button.pack(pady=10)

    def update_slider_value(self, val, param):
        val = int(float(val))
        if param == "exposure":
            self.exposure_value.config(text=str(val))
            mvsdk.CameraSetExposureTime(self.hCamera, val)
        elif param == "gamma":
            self.gamma_value.config(text=str(val))
            mvsdk.CameraSetGamma(self.hCamera, val)
        elif param == "contrast":
            self.contrast_value.config(text=str(val))
            mvsdk.CameraSetContrast(self.hCamera, val)

    def start_stream(self):
        self.running = True
        self.stop_event.clear()
        threading.Thread(target=self.update_frame, daemon=True).start()

    def stop_stream(self):
        self.running = False
        self.stop_event.set()

    def update_frame(self):
        while self.running and not self.stop_event.is_set():
            try:
                pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 200)
                mvsdk.CameraImageProcess(self.hCamera, pRawData, self.pFrameBuffer, FrameHead)
                mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)

                if platform.system() == "Windows":
                    mvsdk.CameraFlipFrameBuffer(self.pFrameBuffer, FrameHead, 1)

                frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    (FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

                self.detect_qr_code(frame)
                frame = cv2.resize(frame, (640, 480))
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = cv2.imencode('.png', img)[1].tobytes()
                photo = tk.PhotoImage(data=img)

                self.video_label.config(image=photo)
                self.video_label.image = photo

            except mvsdk.CameraException as e:
                if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                    print(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")

    def detect_qr_code(self, frame):
        qr_code_detector = cv2.QRCodeDetector()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 81, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        decoded_text, points, _ = qr_code_detector.detectAndDecode(th)

        if points is not None:
            points = points[0].astype(int)
            for j in range(len(points)):
                pt1 = tuple(points[j])
                pt2 = tuple(points[(j + 1) % len(points)])
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        if decoded_text and (time.time() - self.last_qr_print_time) >= self.qr_print_interval:
            self.qr_code_text.set(f"QR Code: {decoded_text}")
            self.last_qr_print_time = time.time()

    def close_app(self):
        self.stop_stream()
        if self.hCamera:
            try:
                mvsdk.CameraUnInit(self.hCamera)
                mvsdk.CameraAlignFree(self.pFrameBuffer)
            except Exception as e:
                print(f"Error during camera cleanup: {e}")
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()
