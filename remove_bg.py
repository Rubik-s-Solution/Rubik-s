import os
from rembg import remove
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import glob
from sklearn.cluster import KMeans

# ============= 기준 색상 정의 =============
REFERENCE_COLORS_RGB = {
    'white':  np.array([220, 230, 240]),
    'yellow': np.array([180, 220, 130]),  # 기존 (230,225,120)에서 실제 클러스터(173,226,125)에 가깝게
    'orange': np.array([200, 100, 80]),   # 더 어두운 주황도 포함 (밝은것~어두운것 중간)
    'red':    np.array([145, 50, 45]),    # 매우 어두운 빨강에 맞춤
    'green':  np.array([55, 180, 110]),   # 기존 (60,190,110)에서 약간 조정
    'blue':   np.array([20, 80, 150])
}

REFERENCE_COLORS_HSV = {
    'white':  np.array([100, 50, 230]),
    'yellow': np.array([73, 180, 180]),   # H 낮춤 (80→73), V 낮춤 (230→180)
    'orange': np.array([10, 150, 200]),   # H 낮춤 (15→10), S 높임, V 낮춤 (어두운 주황)
    'red':    np.array([2, 180, 140]),    # S 높임 (170→180), V 낮춤 (148→140)
    'green':  np.array([60, 180, 200]),   # H 낮춤 (65→60)
    'blue':   np.array([106, 215, 145])
}

def rgb_distance(rgb1, rgb2):
    """RGB 유클리드 거리"""
    return np.sqrt(np.sum((rgb1 - rgb2) ** 2))

def hsv_distance(hsv1, hsv2):
    """HSV 거리 (Hue는 원형)"""
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2
    
    dh = min(abs(h1 - h2), 180 - abs(h1 - h2))
    ds = abs(s1 - s2)
    dv = abs(v1 - v2)
    
    return np.sqrt((dh * 2.0) ** 2 + (ds * 1.0) ** 2 + (dv * 0.8) ** 2)

def match_clusters_to_colors(cluster_centers, reference_colors, distance_func):
    """
    클러스터 중심을 기준 색상에 매칭 (단순 최근접)
    각 클러스터를 가장 가까운 기준 색상에 바로 매칭
    """
    n_clusters = len(cluster_centers)
    color_names = list(reference_colors.keys())
    
    cluster_to_color = {}
    cluster_distances = {}
    
    # 각 클러스터를 가장 가까운 기준 색상에 매칭
    for cluster_id, cluster_center in enumerate(cluster_centers):
        min_distance = float('inf')
        best_color = None
        
        for color_name in color_names:
            ref_color = reference_colors[color_name]
            dist = distance_func(cluster_center, ref_color)
            
            if dist < min_distance:
                min_distance = dist
                best_color = color_name
        
        cluster_to_color[cluster_id] = best_color
        cluster_distances[cluster_id] = min_distance
    
    return cluster_to_color, cluster_distances

def apply_hue_based_rules(cluster_to_color, cluster_centers_hsv):
    """
    Hue + 채도 + 명도 기반 후처리 규칙
    - orange vs red: Hue 범위 더 넓게 (어두운 주황 포함)
    - yellow vs green: Hue 정밀 조정
    """
    for cluster_id in range(len(cluster_centers_hsv)):
        h, s, v = cluster_centers_hsv[cluster_id]
        
        # 1. 흰색 판별 (채도 기반)
        if s < 70:
            cluster_to_color[cluster_id] = 'white'
            continue
        
        # 2. Hue + V + S로 색상 판별
        
        # 빨강/주황 구분 (H=0-30으로 확대)
        if h < 30:
            # 주황 범위 확대: H가 5 이상이면 주황으로 우선 고려
            if h >= 5:
                cluster_to_color[cluster_id] = 'orange'
            # H가 매우 낮으면 (0-5) 명도/채도로 판단
            else:
                if v < 160 and s > 160:  # 어둡고 채도 높으면 빨강
                    cluster_to_color[cluster_id] = 'red'
                else:  # 나머지는 주황
                    cluster_to_color[cluster_id] = 'orange'
        
        # 초록/노랑 구분 (H=50-100)
        elif 50 <= h < 100:
            # 노랑: H=68-82
            if 68 <= h <= 82 and s > 140:
                cluster_to_color[cluster_id] = 'yellow'
            # 초록: 나머지
            else:
                cluster_to_color[cluster_id] = 'green'
        
        # 파랑 (H=100-130)
        elif 100 <= h < 130:
            cluster_to_color[cluster_id] = 'blue'
        
        # 빨강 (H=170-180, 순수 빨강)
        elif h >= 170:
            cluster_to_color[cluster_id] = 'red'
        
        # 기타 (H=30-50): 주황/노랑 경계
        elif 30 <= h < 50:
            if v > 200 and s > 140:  # 밝고 채도 높으면 노랑
                cluster_to_color[cluster_id] = 'yellow'
            else:  # 그 외 주황
                cluster_to_color[cluster_id] = 'orange'
    
    return cluster_to_color

def ensemble_vote(rgb_color, hsv_color, rgb_dist, hsv_dist, hsv_raw=None):
    """
    2중 투표: RGB와 HSV 결과를 종합
    RGB를 훨씬 더 신뢰 (조명 변화에 강건)
    
    Args:
        hsv_raw: 개별 칸의 실제 HSV 값 [H, S, V] (재검증용)
    
    Returns:
        (final_color, confidence, reason)
    """
    # 0. 개별 HSV 재검증 (클러스터링 오류 보정)
    if hsv_raw is not None:
        h, s, v = hsv_raw
        
        # yellow 보정: H=38-60이고 채도 충분하면 무조건 yellow
        if 38 <= h <= 60 and s > 120 and v > 150:
            # RGB도 yellow면 확신
            if rgb_color == 'yellow':
                return 'yellow', 1.0, 'both_agree'
            # RGB가 green이어도 HSV 재검증으로 yellow 확정
            else:
                return 'yellow', 0.95, 'hsv_recheck'
        
        # orange 보정: H=5-10°이고 밝으면 (V>160) 무조건 orange
        if 5 <= h <= 10 and v > 160:
            # RGB도 orange면 확신
            if rgb_color == 'orange':
                return 'orange', 1.0, 'both_agree'
            # RGB가 red여도 HSV 재검증으로 orange 확정
            else:
                return 'orange', 0.95, 'hsv_recheck'
        
        # red 확정: H<5이고 어두우면 (V<160) 무조건 red
        if h < 5 and v < 160 and s > 140:
            if rgb_color == 'red':
                return 'red', 1.0, 'both_agree'
            else:
                return 'red', 0.95, 'hsv_recheck'
    
    # 1. 두 결과 일치 → 확신도 매우 높음
    if rgb_color == hsv_color:
        return rgb_color, 1.0, 'both_agree'
    
    # 2. 불일치 → RGB를 훨씬 더 신뢰
    rgb_confidence = 1.0 / (1.0 + rgb_dist / 50.0)
    hsv_confidence = 1.0 / (1.0 + hsv_dist / 100.0)
    
    # 3. RGB 가중치 3배 (조명 변화에 훨씬 안정적)
    rgb_weighted = rgb_confidence * 3.0
    hsv_weighted = hsv_confidence * 1.0
    
    if rgb_weighted > hsv_weighted:
        final_confidence = rgb_confidence * 0.90
        return rgb_color, final_confidence, 'rgb_wins'
    else:
        final_confidence = hsv_confidence * 0.85
        return hsv_color, final_confidence, 'hsv_wins'

def extract_rgb_from_cell(img_array, row, col, sample_ratio=0.4):
    """셀 중심에서 RGB 추출"""
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
    
    return avg_color

def visualize_results(img_array, colors, confidences, reasons, output_path):
    """결과 시각화"""
    height, width = img_array.shape[:2]
    cell_height = height // 3
    cell_width = width // 3
    
    vis_img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(vis_img)
    
    font_size = int(min(cell_height, cell_width) * 0.10)
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
            
            # 샘플 영역 표시
            draw.rectangle(
                [start_x, start_y, start_x + sample_width, start_y + sample_height],
                outline='red', width=3
            )
            
            color_name = colors[row][col]
            confidence = confidences[row][col]
            reason = reasons[row][col]
            
            # 신뢰도에 따른 색상 및 기호
            if reason == 'both_agree':
                conf_color = 'lime'
                symbol = '✓✓'
            elif confidence >= 0.80:
                conf_color = 'yellow'
                symbol = '✓'
            else:
                conf_color = 'orange'
                symbol = '?'
            
            # 텍스트 배치
            bbox = draw.textbbox((0, 0), color_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = cell_x + (cell_width - text_width) // 2
            text_y = cell_y + cell_height - text_height * 3 - 15
            
            # 배경
            padding = 5
            draw.rectangle(
                [text_x - padding, text_y - padding, 
                 text_x + text_width + padding, text_y + text_height * 3 + padding],
                fill='black'
            )
            
            # 텍스트
            draw.text((text_x, text_y), color_name, fill='white', font=font)
            draw.text((text_x, text_y + text_height), f"{confidence:.0%}", fill=conf_color, font=font)
            draw.text((text_x, text_y + text_height * 2), symbol, fill=conf_color, font=font)
    
    # 그리드
    for i in range(1, 3):
        draw.line([(i * cell_width, 0), (i * cell_width, height)], fill='lime', width=3)
        draw.line([(0, i * cell_height), (width, i * cell_height)], fill='lime', width=3)
    
    vis_img.save(output_path, quality=95)

def order_points(pts):
    """4개 점을 좌상-우상-우하-좌하 순으로 정렬"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def perspective_transform(image, pts):
    """원근 변환"""
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

def process_cube_dual_clustering(input_folder='cube_img', 
                                 output_square_folder='cube_square',
                                 output_vis_folder='cube_visualization',
                                 output_file='cube_colors.txt',
                                 size=800):
    """
    RGB + HSV 이중 클러스터링 앙상블
    - 각 색공간에서 독립적으로 클러스터링
    - 각 클러스터를 가장 가까운 기준 색상에 매칭
    - 두 결과를 투표로 종합
    """
    
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
    
    print("=" * 80)
    print("RGB + HSV 이중 클러스터링 앙상블 방식")
    print(f"총 {len(image_files)}개 이미지 처리")
    print("=" * 80)
    print()
    
    # ========== Phase 1: 배경 제거 및 RGB 수집 ==========
    all_rgb_values = []
    all_images_data = []
    
    print("=" * 80)
    print("Phase 1: 배경 제거 및 RGB 수집")
    print("-" * 80)
    
    for idx, image_path in enumerate(sorted(image_files), 1):
        filename = os.path.basename(image_path)
        print(f"[{idx}/{len(image_files)}] {filename}")
        
        try:
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
            
            square_filename = f"cube_{idx:02d}.jpg"
            square_path = os.path.join(output_square_folder, square_filename)
            square_img.save(square_path, 'JPEG', quality=95)
            
            square_array = np.array(square_img)
            
            # 9개 칸에서 RGB 추출
            for row in range(3):
                for col in range(3):
                    rgb = extract_rgb_from_cell(square_array, row, col)
                    all_rgb_values.append(rgb)
            
            all_images_data.append({
                'filename': square_filename,
                'array': square_array
            })
            
            print(f"  ✓ RGB 수집 완료 (9개 칸)\n")
            
        except Exception as e:
            print(f"  ✗ 오류: {e}\n")
            continue
    
    all_rgb_array = np.array(all_rgb_values)
    total_cells = len(all_rgb_array)
    
    print(f"\n총 {total_cells}개 칸의 데이터 수집 완료")
    print()
    
    # ========== Phase 2-A: RGB 클러스터링 ==========
    print("=" * 80)
    print("Phase 2-A: RGB 클러스터링 (6개 그룹)")
    print("-" * 80)
    
    kmeans_rgb = KMeans(n_clusters=6, random_state=42, n_init=10)
    kmeans_rgb.fit(all_rgb_array)
    
    rgb_cluster_centers = kmeans_rgb.cluster_centers_
    rgb_labels = kmeans_rgb.labels_
    
    print("RGB 클러스터 중심:")
    for i, center in enumerate(rgb_cluster_centers):
        count = np.sum(rgb_labels == i)
        print(f"  클러스터 {i}: RGB({center[0]:.0f}, {center[1]:.0f}, {center[2]:.0f}) - {count}개 칸")
    
    # RGB 클러스터를 색상에 매칭
    rgb_cluster_to_color, rgb_distances = match_clusters_to_colors(
        rgb_cluster_centers, REFERENCE_COLORS_RGB, rgb_distance
    )
    
    print("\nRGB 매칭:")
    for i in sorted(rgb_cluster_to_color.keys()):
        print(f"  클러스터 {i} → {rgb_cluster_to_color[i]:7s} (거리: {rgb_distances[i]:.1f})")
    
    # ========== Phase 2-B: HSV 클러스터링 ==========
    print("\n" + "=" * 80)
    print("Phase 2-B: HSV 클러스터링 (6개 그룹)")
    print("-" * 80)
    
    # RGB를 HSV로 변환
    all_hsv_array = []
    for rgb in all_rgb_array:
        rgb_pixel = np.uint8([[rgb]])
        hsv_pixel = cv2.cvtColor(rgb_pixel, cv2.COLOR_RGB2HSV)
        all_hsv_array.append(hsv_pixel[0][0])
    all_hsv_array = np.array(all_hsv_array)
    
    kmeans_hsv = KMeans(n_clusters=6, random_state=42, n_init=10)
    kmeans_hsv.fit(all_hsv_array)
    
    hsv_cluster_centers = kmeans_hsv.cluster_centers_
    hsv_labels = kmeans_hsv.labels_
    
    print("HSV 클러스터 중심:")
    for i, center in enumerate(hsv_cluster_centers):
        count = np.sum(hsv_labels == i)
        print(f"  클러스터 {i}: HSV(H={center[0]:3.0f}°, S={center[1]:3.0f}, V={center[2]:3.0f}) - {count}개 칸")
    
    # HSV 클러스터를 색상에 매칭
    hsv_cluster_to_color, hsv_distances = match_clusters_to_colors(
        hsv_cluster_centers, REFERENCE_COLORS_HSV, hsv_distance
    )
    
    print("\nHSV 매칭 (후처리 전):")
    for i in sorted(hsv_cluster_to_color.keys()):
        h, s, v = hsv_cluster_centers[i]
        print(f"  클러스터 {i}: H={h:3.0f}° S={s:3.0f} V={v:3.0f} → {hsv_cluster_to_color[i]:7s}")
    
    # Hue 기반 후처리
    hsv_cluster_to_color = apply_hue_based_rules(hsv_cluster_to_color, hsv_cluster_centers)
    
    print("\nHSV 최종 매칭 (후처리 후):")
    for i in sorted(hsv_cluster_to_color.keys()):
        print(f"  클러스터 {i} → {hsv_cluster_to_color[i]:7s}")
    
    # ========== Phase 3: 앙상블 투표 ==========
    print("\n" + "=" * 80)
    print("Phase 3: 앙상블 투표 (RGB + HSV 종합)")
    print("-" * 80)
    print()
    
    results = []
    cell_idx = 0
    
    agree_count = 0
    rgb_win_count = 0
    hsv_win_count = 0
    recheck_count = 0
    
    for img_data in all_images_data:
        filename = img_data['filename']
        square_array = img_data['array']
        
        colors = [[], [], []]
        confidences = [[], [], []]
        reasons = [[], [], []]
        
        for row in range(3):
            for col in range(3):
                rgb_cluster = rgb_labels[cell_idx]
                hsv_cluster = hsv_labels[cell_idx]
                
                rgb_color = rgb_cluster_to_color[rgb_cluster]
                hsv_color = hsv_cluster_to_color[hsv_cluster]
                
                rgb_dist = rgb_distances[rgb_cluster]
                hsv_dist = hsv_distances[hsv_cluster]
                
                # 개별 칸의 실제 HSV 값 전달 (재검증용)
                hsv_raw = all_hsv_array[cell_idx]
                
                final_color, confidence, reason = ensemble_vote(
                    rgb_color, hsv_color, rgb_dist, hsv_dist, hsv_raw
                )
                
                colors[row].append(final_color)
                confidences[row].append(confidence)
                reasons[row].append(reason)
                
                if reason == 'both_agree':
                    agree_count += 1
                elif reason == 'hsv_recheck':
                    recheck_count += 1
                elif reason == 'rgb_wins':
                    rgb_win_count += 1
                else:
                    hsv_win_count += 1
                
                cell_idx += 1
        
        # 시각화
        vis_filename = f"vis_{filename}"
        vis_path = os.path.join(output_vis_folder, vis_filename)
        visualize_results(square_array, colors, confidences, reasons, vis_path)
        
        # 출력 (각 칸의 RGB/HSV 값 포함)
        print(f"\n{filename}:")
        print("=" * 80)
        
        cell_idx_start = cell_idx - 9  # 이 이미지의 첫 칸 인덱스
        
        for r in range(3):
            for c in range(3):
                idx = cell_idx_start + r * 3 + c
                
                # RGB 값
                rgb = all_rgb_array[idx]
                rgb_cluster = rgb_labels[idx]
                rgb_color = rgb_cluster_to_color[rgb_cluster]
                
                # HSV 값
                hsv = all_hsv_array[idx]
                hsv_cluster = hsv_labels[idx]
                hsv_color = hsv_cluster_to_color[hsv_cluster]
                
                # 최종 결과
                final_color = colors[r][c]
                conf = confidences[r][c]
                reason = reasons[r][c]
                
                if reason == 'both_agree':
                    symbol = '✓✓'
                elif reason == 'hsv_recheck':
                    symbol = '✓+'
                elif conf >= 0.80:
                    symbol = '✓'
                else:
                    symbol = '?'
                
                print(f"[{r},{c}] RGB({rgb[0]:3.0f},{rgb[1]:3.0f},{rgb[2]:3.0f}) "
                      f"→ C{rgb_cluster}={rgb_color:6s} | "
                      f"HSV(H={hsv[0]:3.0f}°,S={hsv[1]:3.0f},V={hsv[2]:3.0f}) "
                      f"→ C{hsv_cluster}={hsv_color:6s} | "
                      f"최종: {final_color:6s}({conf:.0%}){symbol}")
        print()
        
        results.append({
            'filename': filename,
            'colors': colors,
            'confidences': confidences
        })
    
    # ========== 통계 ==========
    print("=" * 80)
    print("앙상블 통계")
    print("-" * 80)
    print(f"총 칸 수: {total_cells}")
    print(f"RGB-HSV 일치: {agree_count} ({agree_count/total_cells*100:.1f}%)")
    print(f"HSV 재검증: {recheck_count} ({recheck_count/total_cells*100:.1f}%)")
    print(f"RGB 우세: {rgb_win_count} ({rgb_win_count/total_cells*100:.1f}%)")
    print(f"HSV 우세: {hsv_win_count} ({hsv_win_count/total_cells*100:.1f}%)")
    print("=" * 80)
    
    # 텍스트 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(f"{result['filename']}\n")
            for row_idx, row in enumerate(result['colors']):
                row_conf = result['confidences'][row_idx]
                for col_idx, color in enumerate(row):
                    conf = row_conf[col_idx]
                    f.write(f"{color}({conf:.0%}) ")
                f.write("\n")
            f.write("\n")
    
    print(f"\n모든 처리 완료!")
    print(f"- 정사각형 이미지: '{output_square_folder}'")
    print(f"- 시각화 이미지: '{output_vis_folder}'")
    print(f"- 색상 데이터: '{output_file}'")


if __name__ == "__main__":
    process_cube_dual_clustering(
        input_folder='cube_img',
        output_square_folder='cube_square',
        output_vis_folder='cube_visualization',
        output_file='cube_colors.txt',
        size=800
    )