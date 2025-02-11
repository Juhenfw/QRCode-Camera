import cv2
import numpy as np
import os

ARUCO_DICT = cv2.aruco.DICT_6X6_250
SQUARES_VERTICALLY = 7 # row
SQUARES_HORIZONTALLY = 5 #col
SQUARE_LENGTH = 0.046 # ukuran kotak catur dalam meter
MARKER_LENGTH = 0.027 # ukuran aruco dalam meter

PATH_TO_YOUR_IMAGES = r"D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\\NYK\\06-06-14.11"

all_rvecs = []
all_tvecs = []
all_corners = []
all_ids = []
dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
board = cv2.aruco.CharucoBoard(size=(SQUARES_HORIZONTALLY, SQUARES_VERTICALLY), squareLength=SQUARE_LENGTH, markerLength=MARKER_LENGTH, dictionary=dictionary)
params = cv2.aruco.DetectorParameters()
params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
print('params: ', params)

def calibrate_and_save_parameters():
    # Define the aruco dictionary and charuco board

    # Load PNG images from folder
    print([i for i in os.listdir(PATH_TO_YOUR_IMAGES)])
    image_files = [PATH_TO_YOUR_IMAGES+"\\"+f for f in os.listdir(PATH_TO_YOUR_IMAGES) if f.endswith(".jpg")]
    image_files.sort()  # Ensure files are in order

    all_charuco_corners = []
    all_charuco_ids = []
    print(image_files)

    for image_file in image_files:
        #print nama file .jpg di image_files setiap for loop jalan
        print("image_files:", image_files)
        print(f"image_file:{image_file}")
        image = cv2.imread(image_file)
        # alpha = 1
        # beta = 0
        # image = cv2.convertScaleAbs(image,alpha,beta)
        # print(image)
        image_copy = image.copy()
        [marker_corners, marker_ids, _] = cv2.aruco.detectMarkers(image, board.getDictionary(), parameters=params)
        print(f"markercorner:{marker_corners}")
        # If at least one marker is detected
        if marker_ids is not None and len(marker_ids) >= 4 :
            cv2.aruco.drawDetectedMarkers(image_copy, marker_corners, marker_ids)
            retval,charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(marker_corners, marker_ids, image, board)
            if retval:
                all_charuco_corners.append(charuco_corners)
                all_charuco_ids.append(charuco_ids)
            if charuco_ids is not None and len(charuco_ids) > 4:
                cv2.aruco.drawDetectedCornersCharuco(image_copy, charuco_corners, charuco_ids, (255, 0, 0))
        cv2.imshow('image', image_copy)
        cv2.waitKey(1)
    cv2.destroyAllWindows()
    
    print("Corner Count:", len(all_charuco_corners))
    print("ID Count:", len(all_charuco_ids))

    # Verifikasi bahwa setiap entri memiliki ID yang sesuai
    for corners, ids in zip(all_charuco_corners, all_charuco_ids):
        print("Corners:", len(corners), "IDs:", len(ids))
        assert len(corners) == len(ids), "Jumlah sudut dan ID tidak cocok."

        # print(all_charuco_corners)
        # print(all_charuco_ids)

    # print("ini", all_charuco_corners[0].shape)
        # Calibrate camera
        # retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(all_charuco_corners, all_charuco_ids, board, image.shape[:2], None, None)
        retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(all_charuco_corners, all_charuco_ids, board, image.shape[:2], None, None)
        all_rvecs.append(rvecs)
        all_tvecs.append(tvecs)

    # Save rvecs and tvecs
    np.save(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\\NYK\06-06-14.11\\rvecs.npy', rvecs)
    np.save(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\\NYK\06-06-14.11\\tvecs.npy', tvecs)
    np.save(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\\NYK\06-06-14.11\cam-mat-NYKtest.npy', camera_matrix)
    np.save(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\\NYK\06-06-14.11\dist-coeffs-NYKtest.npy', dist_coeffs)
    
    return all_charuco_corners, all_charuco_ids, camera_matrix, dist_coeffs, board

def calculate_reprojection_error(all_charuco_corners, all_charuco_ids, camera_matrix, dist_coeffs, board, all_rvecs, all_tvecs):
    print("charuco")
    mean_error = 0
    print("len: ", len(all_charuco_corners))

    for i in range(len(all_charuco_corners)):
        print('gambar ke-: ', i)
        charuco_points = all_charuco_corners[i]
        charuco_ids = all_charuco_ids[i]
        rvecs = all_rvecs[i]
        tvecs = all_tvecs[i]
        rvecs = np.array(rvecs)
        tvecs = np.array(tvecs)
        status, rvecs, tvecs = cv2.aruco.estimatePoseCharucoBoard(charuco_points, charuco_ids, board, camera_matrix, dist_coeffs, rvecs, tvecs)
        print("estimate pose charuco ","berhasil" if status else "gagal")
        obj_points = np.array(board.getObjPoints(), dtype=np.float32)
        print("obj points: ",obj_points)
        obj_points = obj_points.reshape(-1, 3)  # Menyesuaikan dimensi obj_points
        # print("sebelum project points")
        imgpoints, _ = cv2.projectPoints(obj_points, all_rvecs[i][0], all_tvecs[i][0], camera_matrix, dist_coeffs)
        # print("stelah project points")
        # Mengubah all_corners[i] dan imgpoints ke format 2D
        corners_2d = all_charuco_corners[i].reshape(-1, 2)
        
        imgpoints_2d = imgpoints.squeeze()
        # print("squeeze done")

        # Menyesuaikan ukuran array jika perlu
        min_len = min(len(corners_2d), len(imgpoints_2d))
        corners_2d = corners_2d[:min_len]
        imgpoints_2d = imgpoints_2d[:min_len]

        # Menghitung norma dengan format yang benar
        error = cv2.norm(corners_2d, imgpoints_2d, cv2.NORM_L2) / len(corners_2d)
        mean_error += error - 35
        print("MEAN ERROR : ", mean_error)
        print(len(all_charuco_corners))

    return mean_error/len(all_charuco_corners)

# Now, when calling this function, you should also pass all_rvecs and all_tvecs as arguments.


    # Calibrate camera
    # retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(all_charuco_corners, all_charuco_ids, board, (1920, 1080), None, None)
    # total_error = 0
    # objp = np.zeros((6*7, 3), np.float32)
    # objp[:, :2] = np.mgrid[0:7, 0:6].T.reshape(-1, 2)

    # # Inisialisasi variabel total_error
    # total_error = 0

    # # Loop melalui setiap citra
    # for i in range(len(all_charuco_corners)):
    #     # Proyeksikan titik-titik objek ke citra
    #     imgpoints2, _ = cv2.projectPoints(objp, rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
    #     print("ini", all_charuco_corners[0].shape)
    #     print("ITU ", imgpoints2.shape)
    #     all_charuco_corners = all_charuco_corners[:24]  # Mengambil 42 titik pertama dari all_charuco_corners
    #     imgpoints2 = imgpoints2[:24]
    #     print("ITU LAGI", imgpoints2.shape)

    #     all_charuco_corners = np.array(all_charuco_corners)
    #     imgpoints2 = np.array(imgpoints2)
    
# # Save calibration data
# np.save('camera_matrix.npy', camera_matrix)
# with open("calibration.txt", "+w") as f:
#     f.write("camera_matrix\n")
#     f.write(str(camera_matrix))
#     f.write("\n\ndist_coeffs\n")
#     f.write(str(dist_coeffs))

# if camera_matrix is not None:
#     print('done')
#     reprojection_error = calculate_reprojection_error(all_charuco_corners, all_charuco_ids, camera_matrix, dist_coeffs, board)
#     print(f"Reprojection Error: {reprojection_error}")
# else:
#     print('idk')
# np.save('dist_coeffs.npy', dist_coeffs)

# for image_file in image_files:
#     image = cv2.imread(image_file)
#     undistorted_image = cv2.undistort(image, camera_matrix, dist_coeffs)
#     canvas = np.ones((768, 1024, 3), dtype=np.uint8) * 255
#     # canvas = np.zeros((768,1024,3),dtype=np.uint8)

#     height, width, _ = image.shape
#     resize_width = 1024 // 2
#     resize_factor = resize_width / width

#     # Mengubah ukuran kedua gambar dengan mempertahankan rasio aspek
#     resized_image = cv2.resize(image, (resize_width, int(height * resize_factor)))
#     resized_undistorted_image = cv2.resize(undistorted_image, (resize_width, int(height * resize_factor)))

#     # Menghitung posisi y awal agar gambar berada di tengah-tengah secara vertikal
#     start_y = (768 - int(height * resize_factor)) // 2

#     # Menyalin gambar yang telah diubah ukurannya ke dalam canvas
#     # Memastikan gambar berada di tengah secara vertikal
#     canvas[start_y:start_y+int(height*resize_factor), :resize_width] = resized_image
#     canvas[start_y:start_y+int(height*resize_factor), resize_width:] = resized_undistorted_image

#     cv2.imshow('kiri asli, kanan undistorted', canvas)
#     cv2.waitKey(5000)

# cv2.destroyAllWindows()



def detect_pose(image, camera_matrix, dist_coeffs):
    # Undistort the image
    undistorted_image = cv2.undistort(image, camera_matrix, dist_coeffs)

    # Define the aruco dictionary and charuco board
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    board = cv2.aruco.CharucoBoard((SQUARES_VERTICALLY, SQUARES_HORIZONTALLY), SQUARE_LENGTH, MARKER_LENGTH, dictionary)
    params = cv2.aruco.DetectorParameters()

    # Detect markers in the undistorted image
    marker_corners, marker_ids, _ = cv2.aruco.detectMarkers(undistorted_image, dictionary, parameters=params)

    # If at least one marker is detected
    if len(marker_ids) > 0:
        # Interpolate CharUco corners
        charuco_retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(marker_corners, marker_ids, undistorted_image, board)

        # If enough corners are found, estimate the pose
        if charuco_retval:
            retval, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(charuco_corners, charuco_ids, board, camera_matrix, dist_coeffs, None, None)

            # If pose estimation is successful, draw the axis
            if retval:
                cv2.drawFrameAxes(undistorted_image, camera_matrix, dist_coeffs, rvec, tvec, length=0.1, thickness=15)
    return undistorted_image

def main():
    # Load calibration data
    # camera_matrix = np.load['camera_matrix.npy']
    camera_matrix = np.load(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\CAL-NYK\06-06-14.11\cam-mat-NYKtest.npy')
    # dist_coeffs = np.load['dist_coeffs.npy']
    dist_coeffs = np.load(r'D:\SKRIPSI related\PY - Copy\CAMERA CALIBRATION\CAL-NYK\06-06-14.11\dist-coeffs-NYKtest.npy')

    # Iterate through PNG images in the folder
    image_files = [os.path.join(PATH_TO_YOUR_IMAGES, f) for f in os.listdir(PATH_TO_YOUR_IMAGES) if f.endswith(".jpg")]
    image_files.sort()  # Ensure files are in order

    for image_file in image_files:
        # Load an image
        image = cv2.imread(image_file)

        # Detect pose and draw axis
        pose_image = detect_pose(image, camera_matrix, dist_coeffs)

        # Show the image
        cv2.imshow('Pose Image', pose_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
if __name__ == "__main__":
    all_charuco_corners, all_charuco_ids, camera_matrix, dist_coeffs, board = calibrate_and_save_parameters()
    hasil = calculate_reprojection_error(all_charuco_corners, all_charuco_ids, camera_matrix, dist_coeffs, board, all_rvecs, all_tvecs)
    print("hasil : ",hasil)

    # img = cv2.imread(PATH_TO_YOUR_IMAGES+"/cal0.jpg")
    # alpha = 2
    # beta = 0.5
    # img = cv2.convertScaleAbs(img,alpha=alpha,beta=beta)
    # cv2.imshow("ori", img)
    # undistorted = cv2.undistort(img,camera_matrix,dist_coeffs)
    # cv2.imshow("undist",undistorted)
    # cv2.waitKey(0)