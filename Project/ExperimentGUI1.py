import mvsdk
import tkinter as tk
from tkinter import ttk
from tkinter import *
from PIL import Image, ImageTk
import numpy as np
import sys

# Global variables for camera settings
horizontal_val = 600
vertical_val = 450
resolution_val = 0

hCamera = None
pFrameBuffer = None
cap = None
running = True

# Function to initialize the camera
def initialize_camera():
    global hCamera, pFrameBuffer, cap

    # Enumerate available cameras
    DevList = mvsdk.CameraEnumerateDevice()
    nDev = len(DevList)

    if nDev < 1:
        print("No camera was found!")
        sys.exit(1)

    # Initialize the first camera
    DevInfo = DevList[0]
    hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

    # Get camera capabilities
    cap = mvsdk.CameraGetCapability(hCamera)

    # Set resolution and format
    set_camera_resolution(hCamera, horizontal_val, vertical_val)
    set_camera_format(hCamera, cap)

    # Set exposure and trigger mode
    mvsdk.CameraSetTriggerMode(hCamera, 0)
    mvsdk.CameraSetAeState(hCamera, 1)
    mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

    # Start the camera
    mvsdk.CameraPlay(hCamera)

    # Allocate buffer for frames
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if cap.sIspCapacity.bMonoSensor else 3)
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

# Function to set camera resolution
def set_camera_resolution(hCamera, width, height):
    image_resolution = mvsdk.CameraGetImageResolution(hCamera)
    image_resolution.iWidth = width
    image_resolution.iHeight = height
    mvsdk.CameraSetImageResolution(hCamera, image_resolution)

# Function to set camera format
def set_camera_format(hCamera, cap):
    if cap.sIspCapacity.bMonoSensor:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
    else:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

# Function to capture a frame from the camera
def capture_frame():
    global hCamera, pFrameBuffer
    try:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        return frame
    except mvsdk.CameraException as e:
        print(f"Failed to capture frame: {e}")
        return None

# Function to update the camera view in the GUI
def update_frame(canvas):
    global running
    if running:
        frame = capture_frame()
        if frame is not None:
            img_original = Image.fromarray(frame)
            img_original_tk = ImageTk.PhotoImage(image=img_original)
            canvas.create_image(0, 0, anchor=tk.NW, image=img_original_tk)
            canvas.image = img_original_tk  # Keep reference to avoid garbage collection
        canvas.after(30, update_frame, canvas)

# Function to stop the camera
def stop_camera():
    global running, hCamera, pFrameBuffer
    running = False
    if hCamera is not None:
        mvsdk.CameraUnInit(hCamera)
    if pFrameBuffer is not None:
        mvsdk.CameraAlignFree(pFrameBuffer)
    print("Camera stopped")

# GUI Setup
def set_default(root):
    root.geometry("1550x900")
    root.resizable(True, True)
    framing = tk.Frame(root, bg='BLACK')
    framing.pack(fill=tk.BOTH, expand=True)
    return framing

# Function to handle camera display in the GUI
def kamera_hasil(framing):
    global running
    canvas = tk.Canvas(framing, bg="white")
    canvas.place(x=350, y=450, width=600, height=450)

    initialize_camera()
    running = True
    update_frame(canvas)

    def on_exit():
        stop_camera()
        root.quit()

    # Exit button to stop camera and exit GUI
    exit_button = tk.Button(framing, text="Exit", command=on_exit, bg="red", fg="white")
    exit_button.place(x=900, y=10, width=100, height=50)

# Main GUI function
def main():
    global root
    root = tk.Tk()
    framing = set_default(root)

    # Start the camera and display the view in GUI
    kamera_hasil(framing)

    root.protocol("WM_DELETE_WINDOW", stop_camera)
    root.mainloop()

if __name__ == "__main__":
    main()
