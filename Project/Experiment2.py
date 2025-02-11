# coding=utf-8
import cv2
import numpy as np
import mvsdk
import platform

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
    
    # Tentukan apakah mode mono atau berwarna
    modeMono = (cap.sIspCapacity.bMonoSensor != 0)

    if modeMono:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
    else:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
    
    # Mulai kamera
    mvsdk.CameraPlay(hCamera)
    
    # Pause kamera untuk mengatur ROI
    mvsdk.CameraPause(hCamera)
    
    # Setting ROI (misal 640x400 dengan offset 0,0)
    set_camera_roi(hCamera, 640, 400, 0, 0)

    # Verifikasi resolusi yang telah diterapkan
    applied_resolution = mvsdk.CameraGetImageResolution(hCamera)
    print(f"Resolusi yang diterapkan: {applied_resolution.iWidth} x {applied_resolution.iHeight}")

    
    # Resume kamera setelah mengatur ROI
    mvsdk.CameraPlay(hCamera)

    print("ROI berhasil diatur ke 640x400 dengan offset (0, 0)")
    
    # Alokasi buffer frame sesuai resolusi maksimum
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if modeMono else 3)
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

    while (cv2.waitKey(1) & 0xFF) != 27:  # Tekan ESC untuk keluar
        try:
            # Mengambil satu frame gambar dari kamera
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
            mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

            # Di Windows, data gambar perlu dibalik vertikal agar benar
            if platform.system() == "Windows":
                mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
            
            # Konversikan buffer frame menjadi format gambar OpenCV
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

            # Pangkas gambar ke ukuran ROI yang diinginkan (640x400 dalam hal ini)
            # Misalkan offset = (0, 0), jadi langsung crop ukuran ROI
            cropped_frame = frame[0:400, 0:640]  # Crop frame sesuai dengan ROI 640x400

            # Tampilkan hasil frame
            cv2.imshow("Hasil ROI - Tekan ESC untuk keluar", cropped_frame)
        
        except mvsdk.CameraException as e:
            if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                print(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")

    # Lepaskan buffer frame
    mvsdk.CameraAlignFree(pFrameBuffer)

    # Matikan kamera setelah selesai
    mvsdk.CameraUnInit(hCamera)
    cv2.destroyAllWindows()