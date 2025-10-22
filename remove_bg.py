import os
from rembg import remove
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import glob
from sklearn.cluster import KMeans
from scipy.optimize import linear_sum_assignment

# ============= 기준 HSV 값 정의 (OpenCV 형식: H=0-180, S=0-255, V=0-255) =============
REFERENCE_COLORS_HSV = {
    'white':  np.array([0, 30, 220]),        # 흰색: 낮은 채도, 높은 명도
    'yellow': np.array([25, 180, 230]),      # 노란색
    'orange': np.array([10, 200, 200]),      # 주황색
    'red':    np.array([0, 200, 180]),       # 빨간색 (어두운 붉은색)
    'green':  np.array([60, 180, 200]),      # 초록색
    'blue':   np.array([105, 180, 210])      # 파란색
}

def hsv_distance(hsv1, hsv2):
    """
    두 HSV 값 사이의 거리 계산
    - Hue는 원형 거리 (0과 180이 가까움)
    - Saturation과 Value는 유클리드 거리
    """
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2
    
    # Hue는 원형 (0과 180이 가까움)
    dh = min(abs(h1 - h2), 180 - abs(h1 - h2))
    ds = abs(s1 - s2)
    dv = abs(v1 - v2)
    
    # 가중치 적용: Hue > Saturation > Value
    return np.sqrt((dh * 2) ** 2 + (ds * 0.5) ** 2 + (dv * 0.3) ** 2)

def extract_rgb_from_cell(img_array, row, col, sample_ratio=0.4):
    """단일 셀에서 RGB 추출"""
    height, width = img_array.shape[:2]
    cell_height = height // 3
    cell_width = width // 3
    
    cell_y = row * cell_height
    cell_x = col * cell_width
    
    sample_height = int(cell_height * sample_ratio)
    sample_width = int(cell_width * sample_ratio)
    start_y = cell_y + (cell_height - sample_height) // 2
    start_x = cell_x + (cell_width - sample_width) // 2
    
    sample_region = img_array[start_y:start_y+sample_height, start_x:start_x+sample_width]
    avg_color = np.mean(sample_region, axis=(0, 1))[:3]
    
    return avg_color, (start_x, start_y, sample_width, sample_height)

def visualize_with_clusters(img_array, colors, cluster_labels, cluster_to_color, output_path):
    """클러스터 결과를 시각화"""
    height, width = img_array.shape[:2]
    cell_height = height // 3
    cell_width = width // 3
    
    vis_img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(vis_img)
    
    font_size = int(min(cell_height, cell_width) * 0.12)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    sample_ratio = 0.4
    
    for row in range(3):
        for col in range(3):
            cell_y = row * cell_height
            cell_x = col * cell_width
            
            sample_height = int(cell_height * sample_ratio)
            sample_width = int(cell_width * sample_ratio)
            start_y = cell_y + (cell_height - sample_height) // 2
            start_x = cell_x + (cell_width - sample_width) // 2
            
            # 샘플링 영역 표시
            draw.rectangle(
                [start_x, start_y, start_x + sample_width, start_y + sample_height],
                outline='red', width=3
            )
            
            # 색상 이름 + 클러스터 번호
            color_name = colors[row][col]
            cluster_num = cluster_labels[row][col]
            text = f"{color_name}\n[{cluster_num}]"
            
            # 텍스트 위치
            bbox = draw.textbbox((0, 0), color_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = cell_x + (cell_width - text_width) // 2
            text_y = cell_y + cell_height - text_height * 2 - 15
            
            # 배경
            padding = 5
            draw.rectangle(
                [text_x - padding, text_y - padding, 
                 text_x + text_width + padding, text_y + text_height * 2 + padding],
                fill='black'
            )
            
            # 텍스트
            draw.text((text_x, text_y), color_name, fill='white', font=font)
            draw.text((text_x, text_y + text_height), f"[{cluster_num}]", fill='yellow', font=font)
    
    # 그리드 선
    for i in range(1, 3):
        draw.line([(i * cell_width, 0), (i * cell_width, height)], fill='lime', width=3)
        draw.line([(0, i * cell_height), (width, i * cell_height)], fill='lime', width=3)
    
    vis_img.save(output_path, quality=95)

# ============= Perspective 변환 함수 =============
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def perspective_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    size = max(maxWidth, maxHeight)
    
    dst = np.array([
        [0, 0],
        [size - 1, 0],
        [size - 1, size - 1],
        [0, size - 1]], dtype="float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (size, size))
    return warped

# ============= 전체 파이프라인 =============
def process_cube_with_reference_matching(input_folder='cube_img', 
                                        output_square_folder='cube_square',
                                        output_vis_folder='cube_visualization',
                                        output_file='cube_colors.txt',
                                        size=800):
    """OpenCV HSV 형식 기반 루빅스 큐브 색상 인식 (수정 버전)"""
    
    # 출력 폴더 생성
    for folder in [output_square_folder, output_vis_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # 이미지 파일 찾기
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_folder, ext)))
    
    if not image_files:
        print(f"'{input_folder}' 폴더에서 이미지를 찾을 수 없습니다.")
        return
    
    print(f"=" * 60)
    print(f"OpenCV HSV 형식 기반 루빅스 큐브 색상 인식 (수정 버전)")
    print(f"총 {len(image_files)}개의 이미지를 처리합니다.")
    print(f"=" * 60)
    print()
    
    print("기준 HSV 값 (OpenCV 형식: H=0-180, S=0-255, V=0-255):")
    for color_name, hsv in REFERENCE_COLORS_HSV.items():
        print(f"  {color_name:7s}: H={hsv[0]:3.0f}° S={hsv[1]:3.0f} V={hsv[2]:3.0f}")
    print()
    
    # Phase 1: 모든 이미지 처리 및 RGB 수집
    all_rgb_values = []
    all_images_data = []
    
    print("=" * 60)
    print("Phase 1: 배경 제거 및 RGB 값 수집")
    print("-" * 60)
    
    for idx, image_path in enumerate(sorted(image_files), 1):
        filename = os.path.basename(image_path)
        print(f"[{idx}/{len(image_files)}] {filename}")
        
        try:
            # 배경 제거 및 전처리
            input_image = Image.open(image_path)
            output_image = remove(input_image)
            if output_image.mode != 'RGBA':
                output_image = output_image.convert('RGBA')
            
            img_array = np.array(output_image)
            alpha = img_array[:, :, 3]
            
            _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                print(f"  ✗ 큐브를 찾을 수 없습니다.\n")
                continue
            
            largest_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            if len(approx) >= 4:
                hull = cv2.convexHull(largest_contour)
                epsilon2 = 0.02 * cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, epsilon2, True)
                
                if len(approx) >= 4:
                    rect = cv2.minAreaRect(largest_contour)
                    box = cv2.boxPoints(rect)
                    box = box.astype(int)
                    warped = perspective_transform(img_array, box.astype("float32"))
                else:
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    warped = img_array[y:y+h, x:x+w]
            else:
                x, y, w, h = cv2.boundingRect(largest_contour)
                warped = img_array[y:y+h, x:x+w]
            
            warped_pil = Image.fromarray(warped)
            warped_pil = warped_pil.resize((size, size), Image.Resampling.LANCZOS)
            square_img = Image.new('RGB', (size, size), (255, 255, 255))
            square_img.paste(warped_pil, (0, 0), warped_pil if warped_pil.mode == 'RGBA' else None)
            
            # 정사각형 이미지 저장
            square_filename = f"cube_{idx:02d}.jpg"
            square_path = os.path.join(output_square_folder, square_filename)
            square_img.save(square_path, 'JPEG', quality=95)
            
            # RGB 값 수집
            square_array = np.array(square_img)
            rgb_grid = []
            
            for row in range(3):
                for col in range(3):
                    rgb, _ = extract_rgb_from_cell(square_array, row, col)
                    rgb_grid.append(rgb)
                    all_rgb_values.append(rgb)
            
            all_images_data.append({
                'filename': square_filename,
                'array': square_array,
                'rgb_grid': rgb_grid
            })
            
            print(f"  ✓ RGB 수집 완료 (9개 칸)\n")
            
        except Exception as e:
            print(f"  ✗ 오류: {e}\n")
            import traceback
            traceback.print_exc()
            continue
    
    # Phase 2: K-means 클러스터링 (RGB 공간에서 수행)
    print("=" * 60)
    print("Phase 2: K-means 클러스터링 (RGB 공간)")
    print("-" * 60)
    
    all_rgb_array = np.array(all_rgb_values)
    print(f"총 {len(all_rgb_array)}개 칸의 RGB 데이터 수집 완료")
    
    # K-means 실행 (k=6, RGB 공간에서)
    kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    kmeans.fit(all_rgb_array)
    
    cluster_centers_rgb = kmeans.cluster_centers_
    all_labels = kmeans.labels_
    
    # RGB 클러스터 중심을 HSV로 변환
    cluster_centers_hsv = []
    for rgb in cluster_centers_rgb:
        # RGB를 OpenCV HSV로 변환
        rgb_pixel = np.uint8([[rgb]])
        hsv_pixel = cv2.cvtColor(rgb_pixel, cv2.COLOR_RGB2HSV)
        cluster_centers_hsv.append(hsv_pixel[0][0])
    cluster_centers_hsv = np.array(cluster_centers_hsv)
    
    print(f"\nK-means 클러스터링 완료!")
    print(f"\n클러스터 중심 HSV (OpenCV 형식):")
    for i, center_hsv in enumerate(cluster_centers_hsv):
        h, s, v = center_hsv
        print(f"  클러스터 {i}: HSV(H={h:3.0f}°, S={s:3.0f}, V={v:3.0f})")
    
    # Phase 3: 클러스터를 기준 색상에 매칭
    print("\n" + "=" * 60)
    print("Phase 3: HSV 색공간에서 클러스터 → 색상 1:1 매칭")
    print("-" * 60)
    
    n_clusters = len(cluster_centers_hsv)
    color_names = list(REFERENCE_COLORS_HSV.keys())
    
    # 비용 행렬 생성
    cost_matrix = np.zeros((n_clusters, len(color_names)))
    
    for i, cluster_hsv in enumerate(cluster_centers_hsv):
        for j, color_name in enumerate(color_names):
            ref_hsv = REFERENCE_COLORS_HSV[color_name]
            cost_matrix[i, j] = hsv_distance(cluster_hsv, ref_hsv)
    
    # 헝가리안 알고리즘으로 최적 매칭
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    cluster_to_color = {}
    for cluster_id, color_id in zip(row_ind, col_ind):
        cluster_to_color[cluster_id] = color_names[color_id]
    
    print("\n매칭 결과:")
    for cluster_id in sorted(cluster_to_color.keys()):
        color_name = cluster_to_color[cluster_id]
        center_hsv = cluster_centers_hsv[cluster_id]
        ref_hsv = REFERENCE_COLORS_HSV[color_name]
        distance = hsv_distance(center_hsv, ref_hsv)
        h, s, v = center_hsv
        print(f"  클러스터 {cluster_id} HSV(H={h:3.0f}°, S={s:3.0f}, V={v:3.0f})")
        print(f"    → {color_name:7s} (기준: H={ref_hsv[0]:.0f}°, S={ref_hsv[1]:.0f}, V={ref_hsv[2]:.0f}, 거리: {distance:.1f})")
    
    # Phase 4: 결과 시각화 및 저장
    print("\n" + "=" * 60)
    print("Phase 4: 결과 시각화 및 저장")
    print("-" * 60)
    
    results = []
    label_idx = 0
    
    for img_data in all_images_data:
        filename = img_data['filename']
        square_array = img_data['array']
        
        # 이 이미지의 9개 칸에 대한 레이블
        image_labels = all_labels[label_idx:label_idx+9].reshape(3, 3)
        label_idx += 9
        
        # 색상 이름 매핑
        colors = []
        for row in range(3):
            row_colors = []
            for col in range(3):
                cluster_id = image_labels[row][col]
                color_name = cluster_to_color[cluster_id]
                row_colors.append(color_name)
            colors.append(row_colors)
        
        # 시각화
        vis_filename = f"vis_{filename}"
        vis_path = os.path.join(output_vis_folder, vis_filename)
        visualize_with_clusters(square_array, colors, image_labels, cluster_to_color, vis_path)
        
        print(f"\n{filename}:")
        for row in colors:
            print(f"  {' '.join(row)}")
        
        results.append({
            'filename': filename,
            'colors': colors
        })
    
    # 텍스트 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(f"{result['filename']}\n")
            for row in result['colors']:
                f.write(f"{' '.join(row)}\n")
            f.write("\n")
    
    print("\n" + "=" * 60)
    print(f"모든 처리 완료!")
    print(f"- 정사각형 이미지: '{output_square_folder}' 폴더")
    print(f"- 시각화 이미지: '{output_vis_folder}' 폴더")
    print(f"- 색상 데이터: '{output_file}' 파일")
    print(f"=" * 60)


if __name__ == "__main__":
    process_cube_with_reference_matching(
        input_folder='cube_img',
        output_square_folder='cube_square',
        output_vis_folder='cube_visualization',
        output_file='cube_colors.txt',
        size=800
    )