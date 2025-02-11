import cv2
import numpy as np
import mvsdk
import time
import platform
import csv
import os

# Nama file CSV
csv_filename = 'qr_code_det.csv'

# Cek apakah file CSV sudah ada atau belum
file_exists = os.path.isfile(csv_filename)

# Inisialisasi file CSV, jika belum ada buat header
with open(csv_filename, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['Timestamp', 'No. Produksi', 'No. Seri', 'Jenis Produk'])

# Inisialisasi kamera
DevList = mvsdk.CameraEnumerateDevice()
if len(DevList) < 1:
    print("No camera was found!")
    exit()

DevInfo = DevList[0]
hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

# Konfigurasi kamera
cap = mvsdk.CameraGetCapability(hCamera)
modeMono = (cap.sIspCapacity.bMonoSensor != 0)

if modeMono:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
else:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

# Set trigger mode dan AE
mvsdk.CameraSetTriggerMode(hCamera, 0)
mvsdk.CameraSetAeState(hCamera, 0)

# Set exposure time, gamma, contrast, dan gain
exposure_time = 13000  # Default 1000 ms
mvsdk.CameraSetExposureTime(hCamera, exposure_time)

gamma_value = 20  # Default gamma 20
mvsdk.CameraSetGamma(hCamera, gamma_value)

contrast_value = 120  # Default contrast 120
mvsdk.CameraSetContrast(hCamera, contrast_value)

gain_value = 16.500  # Default gain 16.500
ui_analog_gain = int(gain_value / 0.125)  # Konversi gain untuk API
mvsdk.CameraSetAnalogGain(hCamera, ui_analog_gain)

# Set white balance manual dan lakukan sekali
mvsdk.CameraSetWbMode(hCamera, 0)
mvsdk.CameraSetOnceWB(hCamera)

# Set ROI settings
W, H = 1280, 1024  # Default ROI width dan height
OH, OV = 0, 0  # Default ROI offsets
resize = mvsdk.tSdkImageResolution(iIndex=0xFF, iHOffsetFOV=OH, iVOffsetFOV=OV, iWidthFOV=W, iHeightFOV=H, iWidth=W, iHeight=H)
mvsdk.CameraSetImageResolution(hCamera, resize)

# Main loop
mvsdk.CameraPlay(hCamera)
FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

last_decoded_text = ""
last_qr_print_time = 0
qr_print_interval = 0.5

while (cv2.waitKey(1) & 0xFF) != 27:  # Tekan ESC untuk keluar
    try:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

        if platform.system() == "Windows":
            mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)

        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        # QR Code detection
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

            if decoded_text:
                top_left = points[0]
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                font_thickness = 2
                text_color = (0, 0, 0)
                line_height = 30
                lines = decoded_text.split('\n')
                for i, line in enumerate(lines):
                    text_position = (top_left[0], top_left[1] - 80 + i * line_height)
                    cv2.putText(frame, line, text_position, font, font_scale, text_color, font_thickness)

        if decoded_text and decoded_text != last_decoded_text and (time.time() - last_qr_print_time) >= qr_print_interval:
            print(f"QR Code detected: {decoded_text}")

            # Save QR code data to CSV
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            data_lines = decoded_text.split('\n')
            no_produksi = data_lines[0].replace('No. Produksi: ', '') if 'No. Produksi' in data_lines[0] else ''
            no_seri = data_lines[1].replace('No. Seri: ', '') if 'No. Seri' in data_lines[1] else ''
            jenis_produk = data_lines[2].replace('Jenis Produk: ', '') if len(data_lines) > 2 and 'Jenis Produk' in data_lines[2] else ''

            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, no_produksi, no_seri, jenis_produk])

            last_decoded_text = decoded_text
            last_qr_print_time = time.time()

        # Display processed frame
        th = cv2.resize(th, (640, 480))
        cv2.imshow("Press ESC to end", th)

    except mvsdk.CameraException as e:
        if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
            print(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")

# Cleanup
mvsdk.CameraUnInit(hCamera)
mvsdk.CameraAlignFree(pFrameBuffer)
cv2.destroyAllWindows()
