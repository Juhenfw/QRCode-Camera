# Modifikasi optimasi untuk mengurangi lag
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
exposure_time = 23 * 1000
mvsdk.CameraSetExposureTime(hCamera, exposure_time)
# Nilai gain yang akan diatur
# gain_value = ctypes.c_float(16.5)  # Nilai yang Anda ingin atur, RANGE 2.5 - 16.5
# Mengatur nilai gain (multiple)
# mvsdk.CameraSetAnalogGain(hCamera, gain_value)

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
# mvsdk.CameraSetGain(hCamera, 320, 251, 135)

''' LUTMODE_PARAM_GEN=0, 
    LUTMODE_PRESET=1,    
    LUTMODE_USER_DEF=2 '''
mvsdk.CameraSetLutMode(hCamera, 0)

# Nilai Gamma
gamma_value = 60 	# Harus INT, nanti tetap dibagi 100
mvsdk.CameraSetGamma(hCamera, gamma_value)

# Mengatur nilai Contrast
contrast_value = 200  # Sesuaikan dengan nilai yang diinginkan
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
        
        # Denoising di interval tertentu
        #if frame_count % 60 == 0:
         # frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

        # Deteksi QR setiap 30 frame
        if frame_count % 1 == 0:
            qr_code_detector = cv2.QRCodeDetector()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ret,th = cv2.threshold(gray,81,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            ret_qr, decoded_text, points, _ = qr_code_detector.detectAndDecodeMulti(th)

            current_time = time.time()

            if points is not None:
                # Menggambar bounding box jika QR Code terdeteksi
                points = points[0].astype(int)  # Koordinat harus dalam bentuk integer
                for j in range(len(points)):
                    pt1 = tuple(points[j])
                    pt2 = tuple(points[(j + 1) % len(points)])  # Loop ke titik awal
                    cv2.line(frame, pt1, pt2, (255, 0, 255), 2)  # Warna Kotak

            if decoded_text and (time.time() - last_qr_print_time) >= qr_print_interval:
                print("QR Code detected: ")
                print(f"{decoded_text}")
                last_qr_print_time = time.time()
                last_no_qr_print_time = time.time()
            elif not decoded_text and (time.time() - last_no_qr_print_time) >= qr_print_interval:
                print("No QR Code detected")
                last_no_qr_print_time = time.time()

        # Memanggil fungsi crosshairs
        # draw_crosshairs(frame, crosshair_positions, crosshair_colors)

        # Jika perlu, resize gambar sebelum ditampilkan
        frame = cv2.resize(frame, (640, 480))
        # th = cv2.resize(th, (640, 480))

        # cv2.imshow("Press ESC to end", th)
        cv2.imshow("Press ESC to end", frame)

        frame_count += 1
        
    except mvsdk.CameraException as e:
        if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
            print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))

# Matikan Kamera
mvsdk.CameraUnInit(hCamera)

# Lepaskan cache frame
mvsdk.CameraAlignFree(pFrameBuffer)

cv2.destroyAllWindows()