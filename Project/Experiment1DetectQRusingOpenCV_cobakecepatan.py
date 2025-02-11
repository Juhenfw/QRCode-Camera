import cv2
import numpy as np
import mvsdk
import time
import platform
import threading

# Inisialisasi Kamera
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

# Pengaturan tambahan
mvsdk.CameraPlay(hCamera)
mvsdk.CameraSetWbMode(hCamera, 0)
mvsdk.CameraSetOnceWB(hCamera)
mvsdk.CameraSetGain(hCamera, 174, 125, 100)

''' LUTMODE_PARAM_GEN=0, 
    LUTMODE_PRESET=1,    
    LUTMODE_USER_DEF=2 '''
mvsdk.CameraSetLutMode(hCamera, 0)

# Nilai Gamma
gamma_value = 74 	# Harus INT, nanti tetap dibagi 100
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
previous_decoded_text = ""

# Fungsi Multithreading
def capture_frame():
    global frame
    while True:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 100)  # Timeout dikurangi
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

def process_frame():
    global frame_count, previous_decoded_text, last_qr_print_time, last_no_qr_print_time
    while True:
        if frame is not None:
            # Denoising jika ada noise yang signifikan
            if frame_count % 60 == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                noise_level = np.std(gray)
                if noise_level > 50:  # Threshold
                    frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

            # Deteksi QR di setiap frame dengan adaptif
            qr_code_detector = cv2.QRCodeDetector()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            decoded_text, points, _ = qr_code_detector.detectAndDecode(gray)

            current_time = time.time()
            if decoded_text != previous_decoded_text:
                if decoded_text and (current_time - last_qr_print_time) >= qr_print_interval:
                    print("QR Code detected: ")
                    print(f"{decoded_text}")
                    last_qr_print_time = current_time
                    last_no_qr_print_time = current_time
                elif not decoded_text and (current_time - last_no_qr_print_time) >= qr_print_interval:
                    print("No QR Code detected")
                    last_no_qr_print_time = current_time
                previous_decoded_text = decoded_text

            # Memanggil fungsi crosshairs
            draw_crosshairs(frame, crosshair_positions, crosshair_colors)

            # Tampilkan gambar penuh, bukan hanya channel 2
            cv2.imshow("Press ESC to end", frame)

            frame_count += 1

# Inisialisasi threading untuk capture dan processing
frame_thread = threading.Thread(target=capture_frame)
processing_thread = threading.Thread(target=process_frame)

frame_thread.start()
processing_thread.start()

while (cv2.waitKey(1) & 0xFF) != 27:
    pass

# Matikan Kamera dan bersihkan resources
mvsdk.CameraUnInit(hCamera)
mvsdk.CameraAlignFree(pFrameBuffer)
cv2.destroyAllWindows()