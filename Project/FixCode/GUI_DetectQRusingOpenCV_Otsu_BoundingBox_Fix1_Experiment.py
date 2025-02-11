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
        self.root.title("QR Code Detector with Enhanced Display")
        self.root.geometry("1000x700")

        # Style Configuration
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=("Helvetica", 12))
        style.configure('Bold.TLabel', background='#f0f0f0', font=("Helvetica", 12, "bold"))
        style.configure('TButton', font=("Helvetica", 12, "bold"))

        self.hCamera = None
        self.frame_count = 0
        self.last_qr_print_time = 0
        self.qr_print_interval = 0.5

        self.qr_code_text = tk.StringVar()
        self.display_mode = tk.StringVar(value="Original")
        self.running = False
        self.stop_event = threading.Event()

        # Initialize camera and build UI
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
        # Main layout
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=1)

        canvas = tk.Canvas(main_frame, bg='#f0f0f0')
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=frame, anchor="nw")

        # Enable scrolling with mouse wheel and touchpad
        def on_mouse_wheel(event):
            if platform.system() == "Windows":
                canvas.yview_scroll(-1 * int(event.delta / 120), "units")
            elif platform.system() == "Darwin":  # macOS
                canvas.yview_scroll(-1 * event.delta, "units")
            else:  # Linux and others
                canvas.yview_scroll(-1 * int(event.delta), "units")

        # Bind the mouse wheel to the scroll functionality
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # macOS compatibility
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # Frame Video
        self.video_label = ttk.Label(frame)
        self.video_label.grid(row=0, column=0, columnspan=4, padx=20, pady=10)

        # Controls Frame - Left
        controls_frame = ttk.Frame(frame)
        controls_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=20)

        # Exposure Time
        ttk.Label(controls_frame, text="Exposure Time (ms):").grid(row=0, column=0, sticky="w", pady=5)
        self.exposure_value = ttk.Entry(controls_frame, width=8)
        self.exposure_value.insert(0, "23000")
        self.exposure_value.grid(row=0, column=2, padx=10)
        self.exposure_value.bind("<Return>", lambda e: self.update_entry_value("exposure"))
        self.exposure_slider = ttk.Scale(
            controls_frame, from_=4.5, to=584358, orient=tk.HORIZONTAL,
            command=lambda val: self.update_slider_value(val, "exposure")
        )
        self.exposure_slider.set(23000)
        self.exposure_slider.grid(row=0, column=1, sticky="ew", padx=10)

        # Gamma
        ttk.Label(controls_frame, text="Gamma:").grid(row=1, column=0, sticky="w", pady=5)
        self.gamma_value = ttk.Entry(controls_frame, width=8)
        self.gamma_value.insert(0, "60")
        self.gamma_value.grid(row=1, column=2, padx=10)
        self.gamma_value.bind("<Return>", lambda e: self.update_entry_value("gamma"))
        self.gamma_slider = ttk.Scale(
            controls_frame, from_=0, to=250, orient=tk.HORIZONTAL,
            command=lambda val: self.update_slider_value(val, "gamma")
        )
        self.gamma_slider.set(60)
        self.gamma_slider.grid(row=1, column=1, sticky="ew", padx=10)

        # Contrast
        ttk.Label(controls_frame, text="Contrast:").grid(row=2, column=0, sticky="w", pady=5)
        self.contrast_value = ttk.Entry(controls_frame, width=8)
        self.contrast_value.insert(0, "200")
        self.contrast_value.grid(row=2, column=2, padx=10)
        self.contrast_value.bind("<Return>", lambda e: self.update_entry_value("contrast"))
        self.contrast_slider = ttk.Scale(
            controls_frame, from_=0, to=200, orient=tk.HORIZONTAL,
            command=lambda val: self.update_slider_value(val, "contrast")
        )
        self.contrast_slider.set(200)
        self.contrast_slider.grid(row=2, column=1, sticky="ew", padx=10)

        # Display Mode
        ttk.Label(controls_frame, text="Display Mode:").grid(row=3, column=0, sticky="w", pady=5)
        self.display_mode_menu = ttk.Combobox(controls_frame, textvariable=self.display_mode, values=["Original", "Threshold"])
        self.display_mode_menu.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10)

        # ROI Settings - Right
        roi_frame = ttk.Frame(frame)
        roi_frame.grid(row=1, column=3, padx=20, pady=20)

        # Using the 'Bold.TLabel' style for a bold title
        ttk.Label(roi_frame, text="ROI Settings", style="Bold.TLabel").grid(row=0, column=0, columnspan=2, pady=10)

        # ROI X Start
        ttk.Label(roi_frame, text="X Start:").grid(row=1, column=0, sticky="w", pady=5)
        self.roi_x_start = ttk.Entry(roi_frame, width=8)
        self.roi_x_start.insert(0, "0")
        self.roi_x_start.grid(row=1, column=1, padx=10)

        # ROI Y Start
        ttk.Label(roi_frame, text="Y Start:").grid(row=2, column=0, sticky="w", pady=5)
        self.roi_y_start = ttk.Entry(roi_frame, width=8)
        self.roi_y_start.insert(0, "0")
        self.roi_y_start.grid(row=2, column=1, padx=10)

        # ROI Width
        ttk.Label(roi_frame, text="Width:").grid(row=3, column=0, sticky="w", pady=5)
        self.roi_width = ttk.Entry(roi_frame, width=8)
        self.roi_width.insert(0, "1280")
        self.roi_width.grid(row=3, column=1, padx=10)

        # ROI Height
        ttk.Label(roi_frame, text="Height:").grid(row=4, column=0, sticky="w", pady=5)
        self.roi_height = ttk.Entry(roi_frame, width=8)
        self.roi_height.insert(0, "1024")
        self.roi_height.grid(row=4, column=1, padx=10)

        # Apply ROI Button
        self.apply_roi_button = ttk.Button(roi_frame, text="Apply ROI", command=self.apply_roi_settings)
        self.apply_roi_button.grid(row=5, column=0, columnspan=2, pady=10)

        # Start, Stop, and Exit buttons
        self.start_button = ttk.Button(frame, text="Start", command=self.start_stream)
        self.start_button.grid(row=2, column=0, padx=20, pady=10)

        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_stream)
        self.stop_button.grid(row=2, column=1, padx=20, pady=10)

        self.exit_button = ttk.Button(frame, text="Exit", command=self.close_app)
        self.exit_button.grid(row=2, column=2, padx=20, pady=10)

        # Label Output QR Code
        ttk.Label(frame, text="QR Code Output:").grid(row=3, column=0, columnspan=4, pady=5)
        self.qr_output_label = ttk.Label(frame, textvariable=self.qr_code_text, font=("Arial", 14))
        self.qr_output_label.grid(row=4, column=0, columnspan=4)

    def apply_roi_settings(self):
        """Apply the ROI settings to the camera."""
        try:
            x_start = int(self.roi_x_start.get())
            y_start = int(self.roi_y_start.get())
            width = int(self.roi_width.get())
            height = int(self.roi_height.get())

            # Configure the resolution using the ROI settings
            resize = mvsdk.tSdkImageResolution(
                iIndex=0xFF, 
                iHOffsetFOV=x_start, 
                iVOffsetFOV=y_start, 
                iWidthFOV=width, 
                iHeightFOV=height, 
                iWidth=width, 
                iHeight=height
            )
            mvsdk.CameraSetImageResolution(self.hCamera, resize)
            messagebox.showinfo("Success", "ROI settings applied successfully.")
        except ValueError:
            messagebox.showerror("Error", "Invalid input for ROI settings. Please enter integer values.")

    def update_slider_value(self, val, param):
        val = int(float(val))
        if param == "exposure":
            self.exposure_value.delete(0, tk.END)
            self.exposure_value.insert(0, str(val))
            mvsdk.CameraSetExposureTime(self.hCamera, val)
        elif param == "gamma":
            self.gamma_value.delete(0, tk.END)
            self.gamma_value.insert(0, str(val))
            mvsdk.CameraSetGamma(self.hCamera, val)
        elif param == "contrast":
            self.contrast_value.delete(0, tk.END)
            self.contrast_value.insert(0, str(val))
            mvsdk.CameraSetContrast(self.hCamera, val)

    def update_entry_value(self, param):
        try:
            if param == "exposure":
                value = int(self.exposure_value.get())
                self.exposure_slider.set(value)  # Update slider
                mvsdk.CameraSetExposureTime(self.hCamera, value)
            elif param == "gamma":
                value = int(self.gamma_value.get())
                self.gamma_slider.set(value)  # Update slider
                mvsdk.CameraSetGamma(self.hCamera, value)
            elif param == "contrast":
                value = int(self.contrast_value.get())
                self.contrast_slider.set(value)  # Update slider
                mvsdk.CameraSetContrast(self.hCamera, value)
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter a valid integer.")

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

                # Display mode handling
                if self.display_mode.get() == "Threshold":
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    _, frame = cv2.threshold(gray, 81, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

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

            # Display the QR code data directly above the bounding box
            if decoded_text:
                # Menghitung posisi teks di atas bounding box
                top_left = points[0]  # Ambil koordinat titik kiri atas
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                font_thickness = 2
                text_color = (0, 0, 0)  # Warna teks
                line_height = 30  # Jarak antar baris

                # Pisahkan teks berdasarkan newline
                lines = decoded_text.split('\n')
                for i, line in enumerate(lines):
                    text_position = (top_left[0], top_left[1] - 80 + i * line_height)  # Geser setiap baris ke bawah
                    # Menambahkan setiap baris teks
                    cv2.putText(frame, line, text_position, font, font_scale, text_color, font_thickness)

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
