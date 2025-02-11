# coding=utf-8
import numpy as np
import mvsdk
import platform
from PIL import Image  # Untuk menyimpan gambar

# Fungsi untuk mengatur resolusi kamera
def set_camera_resolution(hCamera, width, height):
    # Mendapatkan resolusi gambar saat ini dari kamera
    image_resolution = mvsdk.CameraGetImageResolution(hCamera)
    
    # Atur resolusi (width x height)
    image_resolution.iWidth = width
    image_resolution.iHeight = height
    
    # Terapkan resolusi gambar yang telah disetel
    mvsdk.CameraSetImageResolution(hCamera, image_resolution)

# Fungsi untuk mengatur ROI (Region of Interest) kamera
def set_camera_roi(hCamera, width, height, offset_x, offset_y):
    # Mendapatkan resolusi gambar saat ini dari kamera
    image_resolution = mvsdk.CameraGetImageResolution(hCamera)
    
    # Atur mode ROI dan resolusi bidang gambar (width x height)
    image_resolution.iWidth = width
    image_resolution.iHeight = height
    
    # Atur offset untuk bidang pandang (FOV)
    image_resolution.iHOffsetFOV = offset_x
    image_resolution.iVOffsetFOV = offset_y

    # Terapkan resolusi gambar dengan ROI yang telah disetel
    mvsdk.CameraSetImageResolution(hCamera, image_resolution)

# Inisialisasi kamera
DevList = mvsdk.CameraEnumerateDevice()
nDev = len(DevList)

if nDev < 1:
    print("No camera was found!")
else:
    # Pilih kamera pertama
    DevInfo = DevList[0]
    hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
    
    # Dapatkan kemampuan kamera
    cap = mvsdk.CameraGetCapability(hCamera)
    
    # Cek resolusi maksimal dan minimal yang didukung oleh kamera
    print("Resolusi Maksimum yang Didukung: {} x {}".format(cap.sResolutionRange.iWidthMax, cap.sResolutionRange.iHeightMax))
    print("Resolusi Minimum yang Didukung: {} x {}".format(cap.sResolutionRange.iWidthMin, cap.sResolutionRange.iHeightMin))
    
    # Tentukan apakah mode mono atau berwarna
    modeMono = (cap.sIspCapacity.bMonoSensor != 0)

    if modeMono:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
    else:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
    
    # Setting resolusi penuh kamera (misal 720x480)
    full_width = 640
    full_height = 400
    set_camera_resolution(hCamera, full_width, full_height)

    applied_resolution = mvsdk.CameraGetImageResolution(hCamera)
    print(f"Resolusi yang diterapkan: {applied_resolution.iWidth} x {applied_resolution.iHeight}")
    
    # Jika resolusi yang diterapkan tidak sesuai, coba gunakan resolusi yang didukung
    if applied_resolution.iWidth != full_width or applied_resolution.iHeight != full_height:
        print(f"Resolusi {full_width}x{full_height} tidak didukung. Menggunakan resolusi default {applied_resolution.iWidth}x{applied_resolution.iHeight}.")

    # Mulai kamera
    mvsdk.CameraPlay(hCamera)
    
    # Pause kamera untuk mengatur resolusi dan ROI
    mvsdk.CameraPause(hCamera)
    
    
    # Setting ROI (misal 640x400 dengan offset 0,0)
    roi_width = 640
    roi_height = 400
    offset_x = 0
    offset_y = 0
    set_camera_roi(hCamera, roi_width, roi_height, offset_x, offset_y)
    
    # Resume kamera setelah mengatur ROI
    mvsdk.CameraPlay(hCamera)

    # Alokasi buffer frame sesuai resolusi maksimum
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

    try:
        # Mengambil satu frame gambar dari kamera
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

        # Di Windows, data gambar perlu dibalik vertikal agar benar
        if platform.system() == "Windows":
            mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
        
        # Konversikan buffer frame menjadi format gambar numpy
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        # Sekarang crop gambar sesuai dengan ROI
        cropped_frame = frame[offset_y:offset_y+roi_height, offset_x:offset_x+roi_width]

        # Simpan hasil frame yang telah di-crop sebagai gambar
        if modeMono:
            image = Image.fromarray(cropped_frame.squeeze(), 'L')  # 'L' untuk gambar grayscale
        else:
            image = Image.fromarray(cropped_frame, 'RGB')  # 'RGB' untuk gambar berwarna

        # Menyimpan gambar ke file
        image.save("hasil_roi_cropped.png")  # Simpan sebagai PNG (atau JPG jika diinginkan)

        print("Gambar yang terpotong telah disimpan sebagai 'hasil_roi_cropped.png'")
    
    except mvsdk.CameraException as e:
        if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
            print(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")

    # Lepaskan buffer frame
    mvsdk.CameraAlignFree(pFrameBuffer)

    # Matikan kamera setelah selesai
    mvsdk.CameraUnInit(hCamera)
