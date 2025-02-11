#coding=utf-8
import cv2
import numpy as np
import mvsdk
import platform

class Camera(object):
	def __init__(self, DevInfo):
		super(Camera, self).__init__()
		self.DevInfo = DevInfo
		self.hCamera = 0
		self.cap = None
		self.pFrameBuffer = 0

	def open(self):
		if self.hCamera > 0:
			return True

		# Mengaktifkan kamera
		hCamera = 0
		try:
			hCamera = mvsdk.CameraInit(self.DevInfo, -1, -1)
		except mvsdk.CameraException as e:
			print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
			return False

		# Dapatkan deskripsi karakteristik kamera
		cap = mvsdk.CameraGetCapability(hCamera)

		# Menentukan apakah kamera hitam putih atau kamera berwarna
		monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

		# Kamera hitam putih membuat ISP langsung mengeluarkan data MONO, 
		# bukan memperluasnya menjadi data grayscale 24-bit dengan R=G=B
		if monoCamera:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
		else:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

		# Hitung ukuran buffer RGB yang diperlukan, 
		# dan alokasikan langsung sesuai dengan resolusi maksimum kamera
		FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

		# Alokasikan buffer RGB untuk menyimpan gambar yang dikeluarkan oleh ISP
		# Catatan: Data yang ditransmisikan dari kamera ke PC adalah data RAW, yang dikonversi menjadi data RGB di PC melalui ISP perangkat lunak 
		# (jika kamera hitam putih, tidak perlu mengonversi format, tetapi ISP masih memiliki pemrosesan lain, jadi buffer ini tetap perlu dialokasikan)
		pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

		# Ubah mode kamera ke pengambilan gambar berkelanjutan
		mvsdk.CameraSetTriggerMode(hCamera, 0)

		# Pengaturan eksposur manual, waktu eksposur 30 ms
		mvsdk.CameraSetAeState(hCamera, 0)
		mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

		# Biarkan thread pengambilan gambar di dalam SDK mulai bekerja
		mvsdk.CameraPlay(hCamera)

		self.hCamera = hCamera
		self.pFrameBuffer = pFrameBuffer
		self.cap = cap
		return True

	def close(self):
		if self.hCamera > 0:
			mvsdk.CameraUnInit(self.hCamera)
			self.hCamera = 0

		mvsdk.CameraAlignFree(self.pFrameBuffer)
		self.pFrameBuffer = 0

	def grab(self):
		# Ambil satu frame gambar dari kamera
		hCamera = self.hCamera
		pFrameBuffer = self.pFrameBuffer
		try:
			pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
			mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
			mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

			# Pada Windows, data gambar yang diambil terbalik (atas-bawah) dan disimpan dalam format BMP. 
			# Untuk mengonversinya ke OpenCV, gambar perlu dibalik secara vertikal agar posisinya benar
			# Di Linux, gambar langsung keluar dengan orientasi yang benar, tidak perlu dibalik secara vertikal
			if platform.system() == "Windows":
				mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
			
			# Saat ini, gambar sudah tersimpan di pFrameBuffer, dengan pFrameBuffer berisi data RGB untuk kamera berwarna, 
			# dan data grayscale 8-bit untuk kamera hitam putih
			# Konversi pFrameBuffer menjadi format gambar OpenCV untuk pemrosesan algoritma selanjutnya
			frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
			frame = np.frombuffer(frame_data, dtype=np.uint8)
			frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )
			return frame
		except mvsdk.CameraException as e:
			if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
				print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message) )
			return None

def main_loop():
	# Enumerasi kamera
	DevList = mvsdk.CameraEnumerateDevice()
	nDev = len(DevList)
	if nDev < 1:
		print("No camera was found!")
		return

	for i, DevInfo in enumerate(DevList):
		print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))

	cams = []
	for i in map(lambda x: int(x), input("Select cameras: ").split()):
		cam = Camera(DevList[i])
		if cam.open():
			cams.append(cam)

	while (cv2.waitKey(1) & 0xFF) != ord('q'):
		for cam in cams:
			frame = cam.grab()
			if frame is not None:
				frame = cv2.resize(frame, (640,480), interpolation = cv2.INTER_LINEAR)
				cv2.imshow("{} Press q to end".format(cam.DevInfo.GetFriendlyName()), frame)

	for cam in cams:
		cam.close()

def main():
	try:
		main_loop()
	finally:
		cv2.destroyAllWindows()

main()
