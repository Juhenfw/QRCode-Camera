#coding=utf-8
import mvsdk

def main():
	# enumerasi kamera
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

	# mengaktifkan kamera
	hCamera = 0
	try:
		hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
	except mvsdk.CameraException as e:
		print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
		return

	# Dapatkan deskripsi fitur kamera
	cap = mvsdk.CameraGetCapability(hCamera)
	PrintCapbility(cap)

	# Tentukan apakah kamera hitam putih atau kamera berwarna
	monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

	# Untuk kamera hitam putih, biarkan ISP langsung output data MONO, 
	# bukan diperluas menjadi R=G=B dalam format 24-bit grayscale
	if monoCamera:
		mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)

	# Ubah mode kamera menjadi pengambilan gambar berkelanjutan
	mvsdk.CameraSetTriggerMode(hCamera, 0)

	# Eksposur manual, waktu eksposur 30ms
	mvsdk.CameraSetAeState(hCamera, 0)
	mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

	# Mulai jalankan thread pengambilan gambar di dalam SDK
	mvsdk.CameraPlay(hCamera)

	# Hitung ukuran buffer RGB yang dibutuhkan, di sini dialokasikan langsung sesuai resolusi maksimum kamera
	FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

	# Alokasikan buffer RGB untuk menyimpan gambar output dari ISP
	# Catatan: Data yang dikirim dari kamera ke PC adalah data RAW, di PC melalui ISP perangkat lunak dikonversi menjadi data RGB 
	# (jika kamera hitam putih, konversi format tidak diperlukan, tetapi ISP tetap melakukan pemrosesan lain, sehingga buffer ini tetap perlu dialokasikan)
	pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

	# Ambil satu frame gambar dari kamera
	try:
		pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 2000)
		mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
		mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
		
		# Pada titik ini, gambar telah disimpan di pFrameBuffer, untuk kamera berwarna pFrameBuffer = data RGB, 
		# kamera hitam putih pFrameBuffer = data grayscale 8-bit
		# Dalam contoh ini, kita hanya menyimpan gambar ke file hard disk
		status = mvsdk.CameraSaveImage(hCamera, "./grab.bmp", pFrameBuffer, FrameHead, mvsdk.FILE_BMP, 100)
		if status == mvsdk.CAMERA_STATUS_SUCCESS:
			print("Save image successfully. image_size = {}X{}".format(FrameHead.iWidth, FrameHead.iHeight) )
		else:
			print("Save image failed. err={}".format(status) )
	except mvsdk.CameraException as e:
		print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message) )

	# Tutup kamera
	mvsdk.CameraUnInit(hCamera)

	# Bebaskan buffer frame
	mvsdk.CameraAlignFree(pFrameBuffer)

def PrintCapbility(cap):
	for i in range(cap.iTriggerDesc):
		desc = cap.pTriggerDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iImageSizeDesc):
		desc = cap.pImageSizeDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iClrTempDesc):
		desc = cap.pClrTempDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iMediaTypeDesc):
		desc = cap.pMediaTypeDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iFrameSpeedDesc):
		desc = cap.pFrameSpeedDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iPackLenDesc):
		desc = cap.pPackLenDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iPresetLut):
		desc = cap.pPresetLutDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iAeAlmSwDesc):
		desc = cap.pAeAlmSwDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iAeAlmHdDesc):
		desc = cap.pAeAlmHdDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iBayerDecAlmSwDesc):
		desc = cap.pBayerDecAlmSwDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )
	for i in range(cap.iBayerDecAlmHdDesc):
		desc = cap.pBayerDecAlmHdDesc[i]
		print("{}: {}".format(desc.iIndex, desc.GetDescription()) )

main()
