#coding=utf-8
import cv2
import numpy as np
import mvsdk
import time
import platform

class App(object):
	def __init__(self):
		super(App, self).__init__()
		self.pFrameBuffer = 0
		self.quit = False

	def main(self):
		# Enumerasi kamera
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

		# Mengaktifkan kamera
		hCamera = 0
		try:
			hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
		except mvsdk.CameraException as e:
			print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
			return

		# Mendapatkan deskripsi karakteristik kamera
		cap = mvsdk.CameraGetCapability(hCamera)

		# Menentukan apakah kamera hitam putih atau kamera berwarna
		monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

		# Kamera hitam putih membuat ISP langsung mengeluarkan data MONO, 
		# bukan memperluasnya menjadi R=G=B dalam format grayscale 24-bit
		if monoCamera:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
		else:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

		# Mode kamera diubah menjadi pengambilan gambar berkelanjutan
		mvsdk.CameraSetTriggerMode(hCamera, 0)

		# Eksposur manual, waktu eksposur 30 ms
		mvsdk.CameraSetAeState(hCamera, 0)
		mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

		# Memulai thread pengambilan gambar di dalam SDK
		mvsdk.CameraPlay(hCamera)

		# Menghitung ukuran buffer RGB yang diperlukan, di sini 
		# dialokasikan langsung berdasarkan resolusi maksimal kamera
		FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

		# Mengalokasikan buffer RGB, digunakan untuk menyimpan gambar keluaran dari ISP
		# Catatan: Data yang dikirim dari kamera ke PC adalah data RAW, yang dikonversi menjadi data RGB melalui ISP di PC 
		# (Jika kamera hitam putih, tidak perlu mengonversi format, namun ISP masih melakukan pemrosesan lainnya, jadi buffer ini tetap diperlukan)
		self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

		# Mengatur fungsi callback pengambilan gambar
		self.quit = False
		mvsdk.CameraSetCallbackFunction(hCamera, self.GrabCallback, 0)

		# Menunggu untuk keluar
		while not self.quit:
			time.sleep(0.1)

		# Menutup kamera
		mvsdk.CameraUnInit(hCamera)

		# Membebaskan buffer frame
		mvsdk.CameraAlignFree(self.pFrameBuffer)

	@mvsdk.method(mvsdk.CAMERA_SNAP_PROC)
	def GrabCallback(self, hCamera, pRawData, pFrameHead, pContext):
		FrameHead = pFrameHead[0]
		pFrameBuffer = self.pFrameBuffer

		mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
		mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

		# Di Windows, data gambar yang diambil biasanya terbalik secara vertikal dan disimpan dalam format BMP. 
		# Untuk mengonversinya ke OpenCV, gambar tersebut perlu dibalik secara vertikal agar orientasinya benar
		# Di Linux, gambar yang dihasilkan langsung dalam orientasi yang benar, sehingga tidak memerlukan pembalikan vertikal
		if platform.system() == "Windows":
			mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
		
		# Pada saat ini, gambar sudah disimpan di dalam pFrameBuffer, untuk kamera berwarna, pFrameBuffer berisi data RGB, 
		# sedangkan untuk kamera hitam putih, pFrameBuffer berisi data grayscale 8-bit
		# Mengonversi pFrameBuffer menjadi format gambar OpenCV untuk pemrosesan algoritma selanjutnya
		frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
		frame = np.frombuffer(frame_data, dtype=np.uint8)
		frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )

		frame = cv2.resize(frame, (640,480), interpolation = cv2.INTER_LINEAR)
		cv2.imshow("Press q to end", frame)
		if (cv2.waitKey(1) & 0xFF) == ord('q'):
			self.quit = True

def main():
	try:
		app = App()
		app.main()
	finally:
		cv2.destroyAllWindows()

main()
