import mvsdk
import numpy as np
from PIL import Image

''' LUTMODE_PARAM_GEN=0, 
    LUTMODE_PRESET=1,    
    LUTMODE_USER_DEF=2 '''
def set_lut_mode(hCamera, lut_mode):        
    """
    Set the LUT mode on the camera.
    Args:
        hCamera: Handle to the camera
        lut_mode: LUT mode to set, based on emSdkLutMode
    """
    # This is a pseudocode function, replace 'CameraSetLUTMode' with the actual SDK function name if different
    mvsdk.CameraSetLutMode(hCamera, lut_mode)

def apply_custom_lut(hCamera, lut_table):
    """
    Apply a custom LUT table to the camera.
    Args:
        hCamera: Handle to the camera
        lut_table: List or array representing the LUT values
    """
    # Assuming the SDK has a method to set a custom LUT directly. This may vary.
    mvsdk.CameraSetCustomLut(hCamera, lut_table)

# Initialize the camera
DevList = mvsdk.CameraEnumerateDevice()
nDev = len(DevList)
if nDev < 1:
    print("No camera was found!")
    exit()

DevInfo = DevList[0]
hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

# Set LUT mode to dynamically generate LUT based on parameters
set_lut_mode(hCamera, 0) 

# If you want to switch to a preset LUT mode
# set_lut_mode(hCamera, mvsdk.LUTMODE_PRESET)

# For user-defined LUT mode with an example LUT table
# custom_lut_table = [i for i in range(256)]  # Simple identity LUT for example
# set_lut_mode(hCamera, mvsdk.LUTMODE_USER_DEF)
# apply_custom_lut(hCamera, custom_lut_table)

# Start the camera
mvsdk.CameraPlay(hCamera)

# Your camera operations here
# Fungsi untuk mengambil gambar dan menyimpannya
def capture_and_save_image(hCamera):
    try:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 2000)  # Timeout set to 2000 ms
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
        
        # Konversi data gambar ke format yang bisa digunakan
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
        
        # Simpan gambar
        image = Image.fromarray(frame, 'RGB')
        image.save("captured_image.png")
        print("Image saved as 'captured_image.png'")
    except mvsdk.CameraException as e:
        print(f"Failed to capture image: {e}")

# Alokasi buffer memori untuk frame
FrameBufferSize = mvsdk.CameraGetCapability(hCamera).sResolutionRange.iWidthMax * \
                  mvsdk.CameraGetCapability(hCamera).sResolutionRange.iHeightMax * 3
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

capture_and_save_image(hCamera)

# Fungsi untuk mengambil gambar dan menyimpannya
def capture_and_save_image(hCamera):
    try:
        pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 2000)  # Timeout set to 2000 ms
        mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
        mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
        
        # Konversi data gambar ke format yang bisa digunakan
        frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 3))
        
        # Simpan gambar
        image = Image.fromarray(frame, 'RGB')
        image.save("captured_image.png")
        print("Image saved as 'captured_image.png'")
    except mvsdk.CameraException as e:
        print(f"Failed to capture image: {e}")

# Alokasi buffer memori untuk frame
FrameBufferSize = mvsdk.CameraGetCapability(hCamera).sResolutionRange.iWidthMax * \
                  mvsdk.CameraGetCapability(hCamera).sResolutionRange.iHeightMax * 3
pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

capture_and_save_image(hCamera)

# Bebaskan memori yang dialokasikan untuk frame
mvsdk.CameraAlignFree(pFrameBuffer)

# Nonaktifkan kamera
mvsdk.CameraUnInit(hCamera)
print("Camera has been uninitialized.")
