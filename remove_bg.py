import os
from rembg import remove
from PIL import Image
import numpy as np
import cv2
import glob

def order_points(pts):
    """
    4개의 점을 좌상, 우상, 우하, 좌하 순서로 정렬
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # 좌상: 합이 가장 작음, 우하: 합이 가장 큼
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # 우상: 차이가 가장 작음, 좌하: 차이가 가장 큼
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def perspective_transform(image, pts):
    """
    4개의 점을 기준으로 perspective 변환
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # 너비 계산
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    # 높이 계산
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # 정사각형으로 만들기
    size = max(maxWidth, maxHeight)
    
    # 목표 좌표
    dst = np.array([
        [0, 0],
        [size - 1, 0],
        [size - 1, size - 1],
        [0, size - 1]], dtype="float32")
    
    # perspective 변환 행렬 계산
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (size, size))
    
    return warped

def process_cube_images(input_folder='uploaded_images', output_folder='cube_square', 
                        bg_color=(255, 255, 255), size=800):
    """
    루빅스 큐브 이미지를 배경 제거 → perspective 보정 → 정사각형 변환하여 저장합니다.
    
    Parameters:
    - input_folder: 원본 이미지가 있는 폴더
    - output_folder: 처리된 이미지를 저장할 폴더
    - bg_color: 배경색 (R, G, B) 튜플
    - size: 출력 이미지 크기 (정사각형, 픽셀)
    """
    
    # 출력 폴더가 없으면 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 이미지 파일 목록 가져오기
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_folder, ext)))
    
    if not image_files:
        print(f"'{input_folder}' 폴더에서 이미지를 찾을 수 없습니다.")
        return
    
    print(f"총 {len(image_files)}개의 이미지를 처리합니다...")
    print(f"배경색: RGB{bg_color}")
    print(f"출력 크기: {size}x{size} 픽셀\n")
    
    # 각 이미지 처리
    for idx, image_path in enumerate(sorted(image_files), 1):
        try:
            filename = os.path.basename(image_path)
            print(f"처리 중 ({idx}/{len(image_files)}): {filename}")
            
            # 1단계: 이미지 열기
            input_image = Image.open(image_path)
            print(f"  - 원본 크기: {input_image.size}")
            
            # 2단계: 배경 제거
            print(f"  - 배경 제거 중...")
            output_image = remove(input_image)
            
            # RGBA 모드 확인
            if output_image.mode != 'RGBA':
                output_image = output_image.convert('RGBA')
            
            # 3단계: OpenCV 형식으로 변환
            img_array = np.array(output_image)
            
            # 4단계: 알파 채널을 사용해 마스크 생성
            alpha = img_array[:, :, 3]
            
            # 5단계: 큐브의 외곽선 찾기
            # 이진화
            _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
            
            # 컨투어 찾기
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                print(f"  ⚠ 건너뜀: 큐브를 찾을 수 없습니다.\n")
                continue
            
            # 가장 큰 컨투어 선택
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 6단계: 사각형 근사
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # 7단계: perspective 변환
            if len(approx) >= 4:
                # 4개의 점 선택 (가장 큰 사각형)
                hull = cv2.convexHull(largest_contour)
                epsilon2 = 0.02 * cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, epsilon2, True)
                
                # 4개의 코너 점 찾기
                if len(approx) >= 4:
                    # 가장 바깥쪽 4개 점 찾기
                    rect = cv2.minAreaRect(largest_contour)
                    box = cv2.boxPoints(rect)
                    box = box.astype(int)
                    
                    # perspective 변환 적용
                    warped = perspective_transform(img_array, box.astype("float32"))
                    
                    print(f"  - Perspective 보정 완료")
                else:
                    # 사각형을 찾지 못한 경우 bounding box 사용
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    warped = img_array[y:y+h, x:x+w]
                    print(f"  - Bounding box로 크롭")
            else:
                # 컨투어가 충분하지 않으면 bounding box 사용
                x, y, w, h = cv2.boundingRect(largest_contour)
                warped = img_array[y:y+h, x:x+w]
                print(f"  - Bounding box로 크롭")
            
            # 8단계: PIL Image로 변환
            warped_pil = Image.fromarray(warped)
            
            # 9단계: 정사각형으로 리사이즈
            warped_pil = warped_pil.resize((size, size), Image.Resampling.LANCZOS)
            
            # 10단계: RGB 배경에 붙여넣기
            square_img = Image.new('RGB', (size, size), bg_color)
            square_img.paste(warped_pil, (0, 0), warped_pil if warped_pil.mode == 'RGBA' else None)
            
            # 11단계: 파일명 생성 및 저장
            output_filename = f"cube_{idx:02d}.jpg"
            output_path = os.path.join(output_folder, output_filename)
            square_img.save(output_path, 'JPEG', quality=95)
            
            print(f"  ✓ 저장 완료: {output_filename}\n")
            
        except Exception as e:
            print(f"  ✗ 오류 발생 ({filename}): {str(e)}\n")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n모든 이미지 처리 완료!")
    print(f"결과는 '{output_folder}' 폴더에 저장되었습니다.")


if __name__ == "__main__":
    # uploaded_images 폴더의 모든 이미지를 처리
    # 배경 제거 → perspective 보정 → 정면으로 펴기 → 정사각형 저장
    
    process_cube_images(
        input_folder='uploaded_images',   # 원본 이미지 폴더
        output_folder='cube_square',      # 결과 저장 폴더
        bg_color=(255, 255, 255),         # 흰색 배경
        size=800                          # 800x800 픽셀
    )
    
    # 필요한 라이브러리:
    # pip install rembg pillow opencv-python numpy