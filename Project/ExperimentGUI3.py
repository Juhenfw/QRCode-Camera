import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.clock import Clock
import mvsdk
import numpy as np
from kivy.graphics.texture import Texture

class CameraApp(App):
    def build(self):
        # Layout utama
        layout = BoxLayout(orientation='vertical')

        # Widget untuk menampilkan gambar dari kamera
        self.camera_image = Image()
        layout.add_widget(self.camera_image)

        # Tombol untuk memulai kamera
        start_button = Button(text='Start Camera')
        start_button.bind(on_press=self.start_camera)
        layout.add_widget(start_button)

        # Tombol untuk menghentikan kamera
        stop_button = Button(text='Stop Camera')
        stop_button.bind(on_press=self.stop_camera)
        layout.add_widget(stop_button)

        return layout

    def start_camera(self, *args):
        # Inisialisasi kamera
        DevList = mvsdk.CameraEnumerateDevice()
        if len(DevList) < 1:
            print("No camera found!")
            return

        self.DevInfo = DevList[0]
        self.hCamera = mvsdk.CameraInit(self.DevInfo, -1, -1)
        cap = mvsdk.CameraGetCapability(self.hCamera)

        # Atur resolusi dan format output kamera
        self.set_camera_resolution(640, 480)
        if cap.sIspCapacity.bMonoSensor:
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
        else:
            mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

        # Mulai kamera
        mvsdk.CameraPlay(self.hCamera)

        # Alokasikan buffer untuk frame kamera
        FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * 3
        self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

        # Memulai Clock untuk update frame setiap 1/30 detik (30 FPS)
        Clock.schedule_interval(self.update_frame, 1 / 30.0)

    def stop_camera(self, *args):
        # Hentikan kamera dan rilis resource
        Clock.unschedule(self.update_frame)
        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
        if self.pFrameBuffer:
            mvsdk.CameraAlignFree(self.pFrameBuffer)
        print("Camera stopped")

    def set_camera_resolution(self, width, height):
        # Fungsi untuk mengatur resolusi kamera
        image_resolution = mvsdk.CameraGetImageResolution(self.hCamera)
        image_resolution.iWidth = width
        image_resolution.iHeight = height
        mvsdk.CameraSetImageResolution(self.hCamera, image_resolution)

    def update_frame(self, dt):
        try:
            # Ambil frame dari kamera
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 200)
            mvsdk.CameraImageProcess(self.hCamera, pRawData, self.pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)

            # Konversikan frame ke array numpy
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

            # Konversi frame ke Texture Kivy untuk ditampilkan di widget Image
            if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
                # Jika kamera menggunakan format MONO
                texture = Texture.create(size=(FrameHead.iWidth, FrameHead.iHeight), colorfmt='luminance')
            else:
                # Jika kamera menggunakan format warna BGR
                texture = Texture.create(size=(FrameHead.iWidth, FrameHead.iHeight), colorfmt='bgr')

            texture.blit_buffer(frame.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
            texture.flip_vertical()

            # Set texture pada widget Image
            self.camera_image.texture = texture

        except mvsdk.CameraException as e:
            print(f"Failed to capture frame: {e}")

if __name__ == '__main__':
    CameraApp().run()
