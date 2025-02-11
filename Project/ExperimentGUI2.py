import sys
import mvsdk
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import numpy as np
from PIL import Image

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.camera = None
        self.frame_buffer = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def initUI(self):
        # Layout for the GUI
        self.layout = QVBoxLayout()
        
        # Label to show the camera frame
        self.camera_label = QLabel(self)
        self.layout.addWidget(self.camera_label)

        # Start button
        self.start_button = QPushButton('Start Camera', self)
        self.start_button.clicked.connect(self.start_camera)
        self.layout.addWidget(self.start_button)

        # Stop button
        self.stop_button = QPushButton('Stop Camera', self)
        self.stop_button.clicked.connect(self.stop_camera)
        self.layout.addWidget(self.stop_button)

        # Set layout
        self.setLayout(self.layout)
        self.setWindowTitle('Camera Viewer')
        self.show()

    def start_camera(self):
        # Initialize camera
        DevList = mvsdk.CameraEnumerateDevice()
        if len(DevList) < 1:
            print("No camera found!")
            return

        DevInfo = DevList[0]
        self.camera = mvsdk.CameraInit(DevInfo, -1, -1)
        cap = mvsdk.CameraGetCapability(self.camera)

        # Set resolution and format
        self.set_camera_resolution(640, 480)
        if cap.sIspCapacity.bMonoSensor:
            mvsdk.CameraSetIspOutFormat(self.camera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
        else:
            mvsdk.CameraSetIspOutFormat(self.camera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

        # Start the camera
        mvsdk.CameraPlay(self.camera)

        # Allocate frame buffer
        FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * 3
        self.frame_buffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

        # Start timer to capture frames
        self.timer.start(30)

    def stop_camera(self):
        # Stop the camera
        self.timer.stop()
        if self.camera:
            mvsdk.CameraUnInit(self.camera)
        if self.frame_buffer:
            mvsdk.CameraAlignFree(self.frame_buffer)
        self.camera = None
        self.frame_buffer = None

    def update_frame(self):
        # Capture frame from camera
        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.camera, 200)
            mvsdk.CameraImageProcess(self.camera, pRawData, self.frame_buffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(self.camera, pRawData)

            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.frame_buffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))

            # Convert frame to QImage for display
            image = QImage(frame, FrameHead.iWidth, FrameHead.iHeight, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            self.camera_label.setPixmap(pixmap)

        except mvsdk.CameraException as e:
            print(f"Failed to capture frame: {e}")

    def set_camera_resolution(self, width, height):
        image_resolution = mvsdk.CameraGetImageResolution(self.camera)
        image_resolution.iWidth = width
        image_resolution.iHeight = height
        mvsdk.CameraSetImageResolution(self.camera, image_resolution)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CameraApp()
    sys.exit(app.exec_())
