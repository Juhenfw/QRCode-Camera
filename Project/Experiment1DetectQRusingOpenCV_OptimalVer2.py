# Modifikasi optimasi untuk mengurangi lag dengan threading
import cv2
import numpy as np
import mvsdk
import time
import platform
import ctypes
import threading

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
exposure_time = 25 * 1000
mvsdk.CameraSetExposureTime(hCamera, exposure_time)

# Setting resolusi
W = 1280
H = 1024
OH = 0
OV = 0
resize = mvsdk.tSdkImageResolution(iIndex=0XFF, iHOffsetFOV=OH, iVOffsetFOV=OV, iWidthFOV=W, iHeightFOV=H, iWidth=W, iHeight=H)
mvsdk.CameraSetImageResolution(hCamera, resize)

# Pengaturan tambahan
mvsdk.CameraPlay(hCamera)
mvsdk.CameraSetWbMode(hCamera, 0)
mvsdk.CameraSetOnceWB(hCamera)
mvsdk.CameraSetGain(hCamera, 146, 100, 105)

# Frame Buffer
FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

# Fungsi untuk pengambilan frame di thread terpisah
frame = None
lock = threading.Lock()

def capture_frame():
    global frame
    while True:
        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
            mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

            if platform.system() == "Windows":
                mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
            
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
            captured_frame = np.frombuffer(frame_data, dtype=np.uint8)
            captured_frame = captured_frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

            with lock:
                frame = captured_frame

        except mvsdk.CameraException as e:
            if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))

# Memulai thread untuk pengambilan gambar
thread = threading.Thread(target=capture_frame, daemon=True)
thread.start()

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

while (cv2.waitKey(1) & 0xFF) != 27:
    with lock:
        if frame is None:
            continue
        displayed_frame = frame.copy()

    # Hanya lakukan denoising di interval tertentu
    if frame_count % 120 == 0:
        displayed_frame = cv2.fastNlMeansDenoisingColored(displayed_frame, None, 10, 10, 7, 21)

    # Deteksi QR setiap 30 frame
    if frame_count % 30 == 0:
        qr_code_detector = cv2.QRCodeDetector()
        gray = cv2.cvtColor(displayed_frame, cv2.COLOR_BGR2GRAY)
        decoded_text, points, _ = qr_code_detector.detectAndDecode(gray)

        current_time = time.time()
        if decoded_text and (time.time() - last_qr_print_time) >= qr_print_interval:
            print(f"QR Code detected: {decoded_text}")
            last_qr_print_time = time.time()
            last_no_qr_print_time = time.time()
        elif not decoded_text and (time.time() - last_no_qr_print_time) >= qr_print_interval:
            print("No QR Code detected")
            last_no_qr_print_time = time.time()

    # Memanggil fungsi crosshairs
    draw_crosshairs(displayed_frame, crosshair_positions, crosshair_colors)

    # Jika perlu, resize gambar sebelum ditampilkan
    displayed_frame = cv2.resize(displayed_frame, (640, 480))

    # Hanya tampilkan satu channel warna
    cv2.imshow("Press ESC to end", displayed_frame[:,:,2])

    frame_count += 1

# Matikan Kamera
mvsdk.CameraUnInit(hCamera)

# Lepaskan cache frame
mvsdk.CameraAlignFree(pFrameBuffer)

cv2.destroyAllWindows()