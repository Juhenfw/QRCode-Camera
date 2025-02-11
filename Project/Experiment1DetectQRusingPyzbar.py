#coding=utf-8
import cv2
import numpy as np
import mvsdk
import time
import platform
import ctypes
from pyzbar import pyzbar

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

# hCamera = 0
# try:
# 	hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
# except mvsdk.CameraException as e:
# 	print("CameraInit Failed({}): {}".format(e.error_code, e.message) )

print("-------------------------------------------------------------------------")
print("-Camera Information:")
cap = mvsdk.CameraGetCapability(hCamera)
print(cap)
print("-------------------------------------------------------------------------")

modeMono = (cap.sIspCapacity.bMonoSensor != 0)

if modeMono:
	mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
else:
	mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

mvsdk.CameraSetTriggerMode(hCamera, 0) 	# 0 -> Continue
										# 1 -> Software 
										# 2 -> Hardware

mvsdk.CameraSetAeState(hCamera, 0) # Eksposure manual

exposure_time = 25 * 1000	# makin besar makin terang, tetapi FPS drop
mvsdk.CameraSetExposureTime(hCamera, exposure_time) # satuan milisecond
print(f"Waktu eksposur saat ini: {exposure_time/1000} s")

# Setting ROI dan Resolusi
W = 1280
H = 1024
OH = 0
OV = 0

resize = mvsdk.tSdkImageResolution(iIndex=0XFF, iHOffsetFOV=OH, iVOffsetFOV=OV, iWidthFOV=W, iHeightFOV=H, iWidth=W, iHeight=H)
mvsdk.CameraSetImageResolution(hCamera, resize)
# mvsdk.CameraSetFrameRate(hCamera, 30)

mvsdk.CameraPlay(hCamera)

# mvsdk.CameraSetMirror(hCamera, 0, 1) 	# section 2
										# 0 horizontal direction
										# 1 vertical direction

mvsdk.CameraSetWbMode(hCamera, 0)	# 0 manual mode
									# 1 auto mode

mvsdk.CameraSetOnceWB(hCamera) # Trigger White Balance

mvsdk.CameraSetGain(hCamera, 146, 100, 105) # red|green|blue channel gain
										 # nilainya dibagi 100

''' LUTMODE_PARAM_GEN=0, 
    LUTMODE_PRESET=1,    
    LUTMODE_USER_DEF=2 '''
mvsdk.CameraSetLutMode(hCamera, 0)

# Nilai Gamma
gamma_value = 36 	# Harus INT, nanti tetap dibagi 100
mvsdk.CameraSetGamma(hCamera, gamma_value)

# Mengatur nilai Contrast
contrast_value = 115  # Sesuaikan dengan nilai yang diinginkan
mvsdk.CameraSetContrast(hCamera, contrast_value)

# Memeriksa nilai Gamma dan Contrast yang diterapkan
current_gamma = mvsdk.CameraGetGamma(hCamera)
current_contrast = mvsdk.CameraGetContrast(hCamera)
print(f"Gamma saat ini: {current_gamma}, Contrast saat ini: {current_contrast}")


FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
print(f"FrameBufferSize = {FrameBufferSize}")

pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
print(f"pFrameBuffer = {pFrameBuffer}")


# Fungsi untuk Crosshairs
def draw_crosshairs(frame, crosshair_positions, crosshair_colors):
    thickness = 2  # Tebal Garis
    for i, position in enumerate(crosshair_positions):
        x, y = position
        color = crosshair_colors[i]

        # Garis vertikal
        cv2.line(frame, (x, 0), (x, frame.shape[0]), color, thickness)
        # Garis horizontal
        cv2.line(frame, (0, y), (frame.shape[1], y), color, thickness)

# Posisi crosshairs
crosshair_positions = [
    (640, 512),  # Crosshair 1
    (426, 341),  # Crosshair 2
    (853, 682),  # Crosshair 3
]

# Warna crosshairs
crosshair_colors = [
    (0, 0, 255),    # Warna merah untuk crosshair 1 (BGR format)
    (255, 0, 0),    # Warna biru untuk crosshair 2
    (0, 255, 0),    # Warna hijau untuk crosshair 3
]

last_qr_print_time = 0
last_no_qr_print_time = 0
qr_print_interval = 3 # Interval waktu untuk mencetak informasi QR code (dalam detik)

while (cv2.waitKey(1) & 0xFF) != 27: # use ESC to exit
	# Mengambil satu frame gambar dari kamera
	try:
		pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200) # yang kanan -> waktu timeout untuk 1 frame gambar
		mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead) # proses RAW
		mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

		# print(pRawData)
		# print(FrameHead)

		# Di Windows, data gambar yang diambil dari kamera akan terbalik vertikalnya dan disimpan dalam format BMP.
		# Untuk OpenCV, gambar perlu dibalik vertikal agar benar.
		# Di Linux, gambar sudah dalam orientasi yang benar dan tidak perlu dibalik.
		if platform.system() == "Windows":
			mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
		
		# Saat ini, gambar sudah disimpan di pFrameBuffer. Untuk kamera berwarna, pFrameBuffer berisi data RGB. 
		# Untuk kamera hitam-putih, pFrameBuffer berisi data grayscale 8-bit.
		# Konversikan pFrameBuffer menjadi format gambar OpenCV untuk pemrosesan algoritma berikutnya.
		frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
		frame = np.frombuffer(frame_data, dtype=np.uint8)
		frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )

		# Convert image to grayscale (optional, but can help in detection)
		gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

		# Decode the QR code using pyzbar
		decoded_objects = pyzbar.decode(gray_image)

		# Check if any QR code is detected  
		current_time = time.time()  
		if decoded_objects and (current_time - last_qr_print_time) >= qr_print_interval:  
			for obj in decoded_objects:  
				print(f"QR Code Type: {obj.type}")  
				print(f"QR Code Data: {obj.data.decode('utf-8')}")  
				print(f"QR Code Coordinates: {obj.polygon}")  
			last_qr_print_time = current_time  
		elif not decoded_objects and (current_time - last_no_qr_print_time) >= qr_print_interval:  
			print("No QR Code detected")  
			last_no_qr_print_time = current_time  

		# Calling Crosshairs
		draw_crosshairs(frame, crosshair_positions, crosshair_colors)
		# frame = cv2.resize(frame, (1280, 1024), interpolation = cv2.INTER_LINEAR)
		# cv2.imshow("Press ESC to end", frame)

		# cv2.imshow("Press ESC to end", frame[:,:,0])
		cv2.imshow("Press ESC to end", frame)
		# print(frame[:,:,0])
		
	except mvsdk.CameraException as e:
		if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
			print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message) )

# Matikan Kamera
mvsdk.CameraUnInit(hCamera)

# Lepaskan cache frame
mvsdk.CameraAlignFree(pFrameBuffer)

cv2.destroyAllWindows()