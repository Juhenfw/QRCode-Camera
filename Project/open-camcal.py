import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.pyplot import imread

mtx = np.load(r"D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\img\Image\cam-mat.npy")
dist = np.load(r"D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\img\Image\dist-coeffs.npy")

print(mtx)
print("=================================")
print(dist)

img = imread(r"D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\img\Image\HT-SUA134GC-T1V-Snapshot-20240909-154348-375-10390522642383.BMP")
# cv2.imshow("img",img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

undistorted = cv2.undistort(img, mtx, dist)
# cv2.imshow("undist",undistorted)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

plt.figure(figsize=(20,10))
plt.subplot(1,2,1)
plt.imshow(img)
plt.title("Original Image")
plt.subplot(1,2,2)
plt.imshow(undistorted)
plt.title("Undistorted Image")
plt.show()


