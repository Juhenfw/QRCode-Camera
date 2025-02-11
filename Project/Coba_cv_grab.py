#coding=utf-8
import cv2
import numpy as np
import mvsdk
import platform

def main_loop():
	# Enumerasi Kamera
	DevList = mvsdk.CameraEnumerateDevice()
	nDev = len(DevList)
	if nDev < 1:
		print("No camera was found!")
		return

	for i, DevInfo in enumerate(DevList):
		print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
	i = 0 if nDev == 1 else int(input("Select camera: "))
	DevInfo = DevList[i]
	print(DevInfo)

	# Buka kamera
	hCamera = 0
	try:
		hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
	except mvsdk.CameraException as e:
		print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
		return

	# Ambil deskripsi fitur kamera
	cap = mvsdk.CameraGetCapability(hCamera)

	# Menentukan apakah kamera tersebut kamera hitam-putih atau kamera berwarna
	monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

	# Kamera hitam-putih membuat ISP langsung mengeluarkan data MONO, bukan memperluasnya menjadi grayscale 24-bit dengan R=G=B.
	if monoCamera:
		mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
	else:
		mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

	# Ubah mode kamera menjadi pengambilan kontinu.
	mvsdk.CameraSetTriggerMode(hCamera, 0)
	# 0 -> Continue
	# 1 -> Software
	# 2 -> Hardware

	# Pengaturan eksposur manual, waktu eksposur 30ms.
	mvsdk.CameraSetAeState(hCamera, 0) # mode manual
	mvsdk.CameraSetExposureTime(hCamera, 30 * 1000) # satuan milisecond

	# Biarkan thread pengambilan gambar internal SDK mulai bekerja.
	mvsdk.CameraPlay(hCamera)

	# Hitung ukuran buffer RGB yang diperlukan, dan alokasikan berdasarkan resolusi maksimum kamera
	FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)
	print(FrameBufferSize)

	# Alokasikan buffer RGB untuk menyimpan gambar yang dihasilkan oleh ISP 
	# Catatan: Data yang ditransfer dari kamera ke PC adalah data RAW. Di PC, data ini diubah menjadi data RGB melalui ISP perangkat lunak 
	# (jika menggunakan kamera hitam-putih, tidak perlu mengubah format, tetapi ISP masih melakukan pemrosesan lain, jadi buffer ini juga perlu dialokasikan).
	pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
	print(pFrameBuffer)

	while (cv2.waitKey(1) & 0xFF) != 27: # use ESC to exit
		# Mengambil satu frame gambar dari kamera
		try:
			pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200) # yang kanan -> waktu timeout untuk 1 frame gambar
			mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead) # proses RAW
			mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

			print(pRawData)
			print(FrameHead)

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

			frame = cv2.resize(frame, (1280,1024), interpolation = cv2.INTER_LINEAR)
			cv2.imshow("Press ESC to end", frame)
			
		except mvsdk.CameraException as e:
			if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
				print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message) )

	# Matikan Kamera
	mvsdk.CameraUnInit(hCamera)

	# Lepaskan cache frame
	mvsdk.CameraAlignFree(pFrameBuffer)

def main():
	try:
		main_loop()
	finally:
		cv2.destroyAllWindows()

main()
