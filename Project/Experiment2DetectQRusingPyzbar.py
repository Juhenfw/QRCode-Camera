import cv2
import numpy as np
import mvsdk
import time
import platform
import ctypes
import qreader  # Import qreader

# Kamera inisialisasi
DevList = mvsdk.CameraEnumerateDevice()
nDev = len(DevList)
if nDev < 1:
    print("No camera was found!")

for i, DevInfo in enumerate(DevList):
    print(f"nilai i = {i}")
    print(f"{i}: {DevInfo.GetFriendlyName()} {DevInfo.GetPortType()}")
    print(f"Camera {DevInfo.GetFriendlyName()} successfully initialized!")
i = 0 if nDev == 1 else int(input("Select camera: "))
DevInfo = DevList[i]
print(DevInfo)

hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

cap = mvsdk.CameraGetCapability(hCamera)
modeMono = (cap.sIspCapacity.bMonoSensor != 0)

if modeMono:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
else:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

mvsdk.CameraSetTriggerMode(hCamera, 0)
mvsdk.CameraSetAeState(hCamera, 0)
exposure_time = 23 * 1000
mvsdk.CameraSetExposureTime(hCamera, exposure_time)

# Setting resolusi
W = 1280
H = 1024
OH = 0
OV = 0
resize = mvsdk.tSdkImageResolution(iIndex=0XFF, iHOffsetFOV=OH, iVOffsetFOV=OV, iWidthFOV=W, iHeightFOV=H, iWidth=W, iHeight=H)
mvsdk.CameraSetImageResolution(hCamera, resize)

mvsdk.CameraPlay(hCamera)
mvsdk.CameraSetWbMode(hCamera, 0)
mvsdk.CameraSetOnceWB(hCamera)

mvsdk.CameraSetLutMode(hCamera, 0)

# Nilai Gamma dan Contrast
gamma_value = 60
mvsdk.CameraSetGamma(hCamera, gamma_value)

contrast_value = 200
mvsdk.CameraSetContrast(hCamera, contrast_value)

# Frame Buffer
FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

# Crosshairs
def draw_crosshairs(frame, crosshair_positions, crosshair_colors):
    thickness = 2
    for i, position in enumerate(crosshair_positions):
        x, y = position
        color = crosshair_colors[i]
        cv2.line(frame, (x, 0), (x, frame.shape[0]), color, thickness)
        cv2.line(frame, (0, y), (frame.shape[1], y), color, thickness)

crosshair_positions = [(640, 512), (426, 341), (853, 682)]
crosshair_colors = [(0, 0, 255), (255, 0, 0), (0, 255, 0)]
last_qr_print_time = 0
last_no_qr_print_time = 0
qr_print_interval = 0.5
frame_count = 0

# Buat objek QReader
qr_reader = qreader.QReader()

while (cv2.waitKey(1) & 0xFF) != 27:
    try:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

        if platform.system() == "Windows":
            mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
        
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        # Deteksi QR menggunakan qreader
        decoded_data = qr_reader.detect_and_decode(frame)
        
        if decoded_data:
            current_time = time.time()
            if (current_time - last_qr_print_time) >= qr_print_interval:
                print(f"QR Code detected: {decoded_data}")
                last_qr_print_time = current_time
                last_no_qr_print_time = current_time
        elif (time.time() - last_no_qr_print_time) >= qr_print_interval:
            print("No QR Code detected")
            last_no_qr_print_time = time.time()

        draw_crosshairs(frame, crosshair_positions, crosshair_colors)

        th = cv2.resize(frame, (640, 480))
        cv2.imshow("Press ESC to end", th)

        # frame = cv2.resize(frame, (640, 480))
        # cv2.imshow("Press ESC to end", frame)

        frame_count += 1

    except mvsdk.CameraException as e:
        if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
            print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))

# Matikan Kamera
mvsdk.CameraUnInit(hCamera)
mvsdk.CameraAlignFree(pFrameBuffer)
cv2.destroyAllWindows()
