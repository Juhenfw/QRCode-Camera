import cv2
import cupy as cp  # Menggunakan CuPy sebagai pengganti NumPy
import mvsdk
import time
import platform
import csv
import os

# Nama file CSV
csv_filename = 'Ambil_Data.csv'

# Cek apakah file CSV sudah ada atau belum
file_exists = os.path.isfile(csv_filename)

# Inisialisasi file CSV, jika belum ada buat header
with open(csv_filename, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(['Timestamp', 'No. Produksi', 'No. Seri', 'Jenis Produk', 'Kecepatan Deteksi (ms)', 'Status Deteksi'])

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

# Optimasi kamera
if modeMono:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
else:
    mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

# Matikan AE dan sesuaikan waktu eksposur untuk objek bergerak cepat
mvsdk.CameraSetTriggerMode(hCamera, 0)
mvsdk.CameraSetAeState(hCamera, 0)
exposure_time = 13 * 1000  # Kurangi waktu eksposur untuk kecepatan konveyor 30 m/min
mvsdk.CameraSetExposureTime(hCamera, exposure_time)

# Resolusi kamera
W, H = 1280, 1024
resize = mvsdk.tSdkImageResolution(iIndex=0XFF, iHOffsetFOV=0, iVOffsetFOV=0, iWidthFOV=W, iHeightFOV=H, iWidth=W, iHeight=H)
mvsdk.CameraSetImageResolution(hCamera, resize)

# Set gamma dan kontras untuk kecepatan tinggi
gamma_value = 30  # Pengaturan yang lebih rendah untuk visibilitas di objek cepat
mvsdk.CameraSetGamma(hCamera, gamma_value)

contrast_value = 180
mvsdk.CameraSetContrast(hCamera, contrast_value)

# Mulai kamera dan pengaturan lain
mvsdk.CameraPlay(hCamera)
mvsdk.CameraSetWbMode(hCamera, 0)
mvsdk.CameraSetOnceWB(hCamera)
mvsdk.CameraSetLutMode(hCamera, 0)

FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

qr_print_interval = 0.5
last_qr_print_time = 0
last_no_qr_print_time = 0
last_decoded_text = ""

while (cv2.waitKey(1) & 0xFF) != 27:
    try:
        start_time = time.time()  # Start time for speed calculation

        # Ambil gambar dari kamera
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

        if platform.system() == "Windows":
            mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)

        # Konversi buffer gambar ke array CuPy
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = cp.frombuffer(frame_data, dtype=cp.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        # Deteksi QR Code
        qr_code_detector = cv2.QRCodeDetector()
        gray = cv2.cvtColor(cp.asnumpy(frame), cv2.COLOR_BGR2GRAY)  # Konversi CuPy ke NumPy sementara untuk operasi OpenCV
        _, th = cv2.threshold(gray, 81, 255, cv2.THRESH_BINARY)  # Sesuaikan threshold untuk objek cepat
        decoded_text, points, _ = qr_code_detector.detectAndDecode(th)

        # Hitung kecepatan deteksi
        detection_speed_ms = (time.time() - start_time) * 1000  # dalam ms

        current_time = time.time()
        formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))

        if points is not None:
            points = cp.array(points[0].astype(int))
            for j in range(len(points)):
                pt1 = tuple(points[j])
                pt2 = tuple(points[(j + 1) % len(points)])
                cv2.line(cp.asnumpy(frame), pt1, pt2, (0, 255, 0), 2)  # Konversi CuPy ke NumPy untuk operasi cv2

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
                    cv2.putText(cp.asnumpy(frame), line, text_position, font, font_scale, text_color, font_thickness)

        # Catat hasil deteksi
        if decoded_text and decoded_text != last_decoded_text and (time.time() - last_qr_print_time) >= qr_print_interval:
            print("QR Code detected: ")
            print(f"{decoded_text}")

            data_lines = decoded_text.split('\n')
            no_produksi = data_lines[0].replace('No. Produksi: ', '') if 'No. Produksi' in data_lines[0] else ''
            no_seri = data_lines[1].replace('No. Seri: ', '') if 'No. Seri' in data_lines[1] else ''
            jenis_produk = data_lines[2].replace('Jenis Produk: ', '') if len(data_lines) > 2 and 'Jenis Produk' in data_lines[2] else ''

            # Simpan ke CSV
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([formatted_time, no_produksi, no_seri, jenis_produk, detection_speed_ms, "Berhasil"])

            last_decoded_text = decoded_text
            last_qr_print_time = time.time()
            last_no_qr_print_time = time.time()

        elif not decoded_text and (time.time() - last_no_qr_print_time) >= qr_print_interval:
            print("No QR Code detected")
            last_no_qr_print_time = time.time()
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([formatted_time, "", "", "", detection_speed_ms, "Gagal"])

        # Tampilkan hasil deteksi
        th = cp.asnumpy(cp.resize(th, (640, 480)))  # Konversi CuPy ke NumPy untuk ditampilkan
        cv2.imshow("Press ESC to end", th)

    except mvsdk.CameraException as e:
        if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
            print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))

# Bersihkan kamera
mvsdk.CameraUnInit(hCamera)
mvsdk.CameraAlignFree(pFrameBuffer)
cv2.destroyAllWindows()
