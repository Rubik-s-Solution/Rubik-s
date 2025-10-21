import os
import io
import uuid
import sys
import subprocess
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    aiofiles = None
    HAS_AIOFILES = False
from PIL import Image
import json
import cv2
import numpy as np
from sklearn.cluster import KMeans
from scipy.optimize import linear_sum_assignment

try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("경고: rembg 라이브러리가 설치되지 않았습니다. 배경 제거 없이 진행됩니다.")

app = FastAPI(title="Rubik's Cube Image API", version="1.0.0")

# CORS 설정 (프론트엔드와 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드된 이미지를 저장할 디렉토리 설정
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# 정적 파일 서빙 (업로드된 이미지에 접근하기 위해)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

# 세션 관리
SESSIONS = {}  # {session_id: {"created_at": datetime, "images": {...}}}

def get_session_id(request=None) -> str:
    """요청에서 세션 ID 가져오기 또는 새로 생성"""
    # 헤더에서 세션 ID 확인
    if request and hasattr(request, 'headers'):
        session_id = request.headers.get('X-Session-Id')
        if session_id and session_id in SESSIONS:
            return session_id
    
    # 새 세션 생성
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "created_at": datetime.now(),
        "images": {}
    }
    return session_id

def get_session_upload_dir(session_id: str) -> Path:
    """세션별 업로드 디렉토리 반환"""
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    return session_dir

def validate_session(session_id: str) -> bool:
    """세션 ID 유효성 확인"""
    return session_id in SESSIONS

# 큐브 면 정보
CUBE_FACES = ["U", "D", "F", "B", "L", "R"]

# 허용된 이미지 확장자
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

def validate_image_file(file: UploadFile) -> None:
    """이미지 파일 유효성 검사"""
    # 파일 이름이 None인 경우 체크
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="파일 이름이 없습니다."
        )
    
    # 파일 확장자 확인
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 파일 크기 확인 (Content-Length 헤더가 있는 경우)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 너무 큽니다. 최대 크기: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def validate_cube_face(face: str) -> None:
    """큐브 면 유효성 검사"""
    if face not in CUBE_FACES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 큐브 면입니다. 허용된 면: {', '.join(CUBE_FACES)}"
        )

@app.get("/")
async def main():
    return {
        "message": "Rubik's Cube Image Upload API",
        "version": "1.0.0",
        "endpoints": {
            "create_session": "/create-session",
            "delete_session": "/delete-session",
            "upload": "/upload-image",
            "images": "/images/{session_id}/{filename}",
            "cube_images": "/cube-images",
            "analyze": "/analyze-cube-images",
            "health": "/health"
        }
    }

@app.post("/create-session")
async def create_session():
    """새로운 세션 생성"""
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "created_at": datetime.now(),
        "images": {}
    }
    
    # 세션 디렉토리 생성
    session_dir = get_session_upload_dir(session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "세션이 생성되었습니다.",
        "created_at": SESSIONS[session_id]["created_at"].isoformat()
    }

@app.delete("/delete-session")
async def delete_session(request: Request):
    """
    세션 삭제 및 관련 파일 정리
    세션 ID는 X-Session-Id 헤더로 전달
    """
    # 헤더에서 세션 ID 가져오기
    session_id = request.headers.get('X-Session-Id')
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
    
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 세션 디렉토리 삭제
    session_dir = UPLOAD_DIR / session_id
    if session_dir.exists():
        import shutil
        shutil.rmtree(session_dir)
    
    # 세션 정보 삭제
    del SESSIONS[session_id]
    
    return {
        "success": True,
        "message": "세션이 삭제되었습니다."
    }

@app.post("/upload-image")
async def upload_image(
    request: Request,
    face: str = Form(..., description="큐브 면 (U, D, F, B, L, R)"),
    file: UploadFile = File(..., description="업로드할 이미지 파일")
):
    """
    큐브의 특정 면에 이미지 업로드 (세션별 분리)
    세션 ID는 X-Session-Id 헤더로 전달
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
        
        # 세션 유효성 검사 - 없으면 새로 생성
        if not validate_session(session_id):
            print(f"세션 {session_id}가 존재하지 않습니다. 새로 생성합니다.")
            SESSIONS[session_id] = {
                "created_at": datetime.now(),
                "images": {}
            }
        
        # 유효성 검사
        validate_cube_face(face)
        validate_image_file(file)
        
        # 파일 내용 읽기 및 크기 검사
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 크기: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # 이미지 파일인지 PIL로 검증
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # 이미지 무결성 검사
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="유효하지 않은 이미지 파일입니다."
            )
        
        # 고유한 파일명 생성
        if file.filename is None:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{face}_{uuid.uuid4().hex}{file_extension}"
        
        # 세션별 디렉토리에 저장
        session_dir = get_session_upload_dir(session_id)
        file_path = session_dir / unique_filename
        
        # 파일 저장
        if HAS_AIOFILES:
            async with aiofiles.open(file_path, 'wb') as f:  # type: ignore
                await f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        # 이미지 정보 저장 (메타데이터)
        metadata = {
            "face": face,
            "original_filename": file.filename,
            "saved_filename": unique_filename,
            "file_size": len(content),
            "content_type": file.content_type,
            "upload_time": datetime.now().isoformat(),
            "image_url": f"/images/{session_id}/{unique_filename}",
            "session_id": session_id
        }
        
        # 메타데이터 파일 저장
        metadata_path = session_dir / f"{unique_filename}.json"
        if HAS_AIOFILES:
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:  # type: ignore
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
        else:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
        
        # 세션에 이미지 정보 추가
        SESSIONS[session_id]["images"][face] = metadata
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{face} 면에 이미지가 성공적으로 업로드되었습니다.",
                "data": metadata,
                "session_id": session_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/cube-images")
async def get_cube_images(request: Request):
    """
    특정 세션의 업로드된 모든 큐브 이미지 정보 조회
    세션 ID는 X-Session-Id 헤더로 전달
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
        
        # 세션 유효성 검사
        if not validate_session(session_id):
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        # 세션 데이터에서 직접 가져오기
        images_info = SESSIONS[session_id]["images"]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "큐브 이미지 정보를 성공적으로 조회했습니다.",
                "session_id": session_id,
                "data": images_info
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.delete("/cube-images/{face}")
async def delete_cube_image(request: Request, face: str):
    """
    특정 세션의 특정 면 이미지 삭제
    세션 ID는 X-Session-Id 헤더로 전달
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
        
        # 세션 유효성 검사
        if not validate_session(session_id):
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        validate_cube_face(face)
        
        # 세션 데이터에서 이미지 정보 확인
        if face not in SESSIONS[session_id]["images"]:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"{face} 면에 업로드된 이미지가 없습니다."
                }
            )
        
        metadata = SESSIONS[session_id]["images"][face]
        session_dir = get_session_upload_dir(session_id)
        deleted_files = []
        
        # 이미지 파일 삭제
        image_file = session_dir / metadata["saved_filename"]
        if image_file.exists():
            os.remove(image_file)
            deleted_files.append(str(image_file))
        
        # 메타데이터 파일 삭제
        metadata_file = session_dir / f"{metadata['saved_filename']}.json"
        if metadata_file.exists():
            os.remove(metadata_file)
            deleted_files.append(str(metadata_file))
        
        # 세션 데이터에서 제거
        del SESSIONS[session_id]["images"][face]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{face} 면의 이미지가 성공적으로 삭제되었습니다.",
                "deleted_files": deleted_files,
                "session_id": session_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 삭제 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    API 상태 확인
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "upload_dir": str(UPLOAD_DIR),
        "upload_dir_exists": UPLOAD_DIR.exists()
    }

# ==================== K-means 클러스터링 기반 색상 분석 (remove_bg.py에서 가져옴) ====================

# 기준 RGB 값 정의
REFERENCE_COLORS = {
    'white':  np.array([255, 255, 255]),  # 흰색
    'yellow': np.array([255, 255, 0]),    # 노란색
    'orange': np.array([255, 165, 0]),    # 주황색
    'red':    np.array([180, 0, 0]),      # 빨간색
    'green':  np.array([0, 155, 0]),      # 초록색
    'blue':   np.array([0, 0, 255])       # 파란색
}

def rgb_distance(rgb1, rgb2):
    """두 RGB 값 사이의 유클리드 거리"""
    return np.sqrt(np.sum((rgb1 - rgb2) ** 2))

def assign_clusters_to_colors(cluster_centers):
    """
    클러스터 중심을 기준 색상에 1:1 매칭
    헝가리안 알고리즘 사용 (중복 없는 최적 매칭)
    """
    n_clusters = len(cluster_centers)
    color_names = list(REFERENCE_COLORS.keys())
    
    # 비용 행렬 생성 (거리 = 비용)
    cost_matrix = np.zeros((n_clusters, len(color_names)))
    
    for i, cluster_center in enumerate(cluster_centers):
        for j, color_name in enumerate(color_names):
            ref_rgb = REFERENCE_COLORS[color_name]
            cost_matrix[i, j] = rgb_distance(cluster_center, ref_rgb)
    
    # 헝가리안 알고리즘으로 최적 매칭
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # 매칭 결과
    cluster_to_color = {}
    for cluster_id, color_id in zip(row_ind, col_ind):
        cluster_to_color[cluster_id] = color_names[color_id]
    
    return cluster_to_color

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
    
    return avg_color

def order_points(pts):
    """Perspective 변환을 위한 4점 정렬"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def perspective_transform(image, pts):
    """Perspective 변환으로 면 정사각형 만들기"""
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

def detect_cube_contour(image_array):
    """이미지에서 큐브 윤곽 검출"""
    # 그레이스케일 변환
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array
    
    # 이진화
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
    
    # 윤곽 검출
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # 가장 큰 윤곽 선택
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 윤곽 근사화
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    if len(approx) >= 4:
        hull = cv2.convexHull(largest_contour)
        epsilon2 = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon2, True)
        
        if len(approx) >= 4:
            rect = cv2.minAreaRect(largest_contour)
            box = cv2.boxPoints(rect)
            return box.astype("float32")
    
    # 실패시 바운딩 박스 반환
    x, y, w, h = cv2.boundingRect(largest_contour)
    return np.array([
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h]
    ], dtype="float32")

def preprocess_cube_image(image_path: Path, target_size=800, use_rembg=True):
    """
    큐브 이미지 전처리 및 정사각형 변환
    
    Args:
        image_path: 이미지 파일 경로
        target_size: 출력 이미지 크기
        use_rembg: 배경 제거 사용 여부 (rembg 라이브러리 필요)
    
    Returns:
        전처리된 이미지 배열 (RGB, target_size x target_size)
    """
    # 이미지 읽기
    img = Image.open(image_path)
    
    # 배경 제거 (rembg 사용 가능 시)
    if use_rembg and HAS_REMBG:
        try:
            img = remove(img)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            print(f"  배경 제거 완료: {image_path.name}")
        except Exception as e:
            print(f"  배경 제거 실패, 원본 사용: {e}")
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
    
    # RGB 변환 및 윤곽 검출
    if img.mode == 'RGBA':
        # 알파 채널을 이용한 윤곽 검출
        img_array = np.array(img)
        alpha = img_array[:, :, 3]
        
        # 윤곽 검출
        contour_pts = detect_cube_contour(alpha)
        
        if contour_pts is not None:
            # Perspective 변환
            warped = perspective_transform(img_array, contour_pts)
            warped_pil = Image.fromarray(warped)
        else:
            warped_pil = img
    else:
        # RGB 이미지인 경우 그대로 사용
        img_array = np.array(img.convert('RGB'))
        contour_pts = detect_cube_contour(img_array)
        
        if contour_pts is not None:
            warped = perspective_transform(img_array, contour_pts)
            warped_pil = Image.fromarray(warped)
        else:
            warped_pil = img.convert('RGB')
    
    # 크기 조정
    warped_pil = warped_pil.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    # RGB 배경에 붙이기
    square_img = Image.new('RGB', (target_size, target_size), (255, 255, 255))
    square_img.paste(warped_pil, (0, 0), warped_pil if warped_pil.mode == 'RGBA' else None)
    
    return np.array(square_img)

# 색상 레이블 매핑 (K-means 결과를 단일 문자로 변환)
COLOR_LABEL_MAP = {
    'white': 'w',
    'yellow': 'y',
    'orange': 'o',
    'red': 'r',
    'green': 'g',
    'blue': 'b'
}

# 색상 레이블을 HEX 색상으로 변환
COLOR_MAP = {
    "w": "#FFFFFF",  # white
    "y": "#FFD500",  # yellow
    "o": "#FF5800",  # orange
    "r": "#C41E3A",  # red
    "g": "#009E60",  # green
    "b": "#0051BA",  # blue
}

@app.post("/analyze-cube-images")
async def analyze_cube_images(request: Request):
    """
    특정 세션의 업로드된 모든 큐브 이미지를 K-means 클러스터링으로 분석하여 색상 데이터 추출
    전체 큐브(54개 칸)를 한번에 분석하여 일관성 있는 색상 인식
    세션 ID는 X-Session-Id 헤더로 전달
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
        
        # 세션 유효성 검사
        if not validate_session(session_id):
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        # 세션 데이터에서 이미지 정보 가져오기
        images_info = SESSIONS[session_id]["images"]
        session_dir = get_session_upload_dir(session_id)
        
        if not images_info:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "분석할 이미지가 없습니다. 먼저 이미지를 업로드하세요.",
                    "session_id": session_id
                }
            )
        
        # Phase 1: 모든 이미지 전처리 및 RGB 수집
        all_rgb_values = []
        all_images_data = []
        
        print(f"\n[세션 {session_id[:8]}...] Phase 1: {len(images_info)}개 이미지 전처리 시작")
        
        for face, metadata in sorted(images_info.items()):
            image_path = session_dir / metadata["saved_filename"]
            
            try:
                # 이미지 전처리 (배경 제거 + Perspective 변환)
                square_array = preprocess_cube_image(image_path)
                
                # 각 칸에서 RGB 추출
                rgb_grid = []
                for row in range(3):
                    for col in range(3):
                        rgb = extract_rgb_from_cell(square_array, row, col)
                        rgb_grid.append(rgb)
                        all_rgb_values.append(rgb)
                
                all_images_data.append({
                    'face': face,
                    'array': square_array,
                    'rgb_grid': rgb_grid
                })
                
                print(f"  {face} 면: RGB 수집 완료 (9개 칸)")
                
            except Exception as e:
                print(f"  {face} 면 처리 실패: {e}")
                continue
        
        if len(all_rgb_values) < 54:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"충분한 데이터가 없습니다. {len(all_rgb_values)}개 칸 수집됨 (최소 54개 필요)",
                    "session_id": session_id
                }
            )
        
        # Phase 2: K-means 클러스터링 (54개 칸 → 6개 그룹)
        print(f"\nPhase 2: K-means 클러스터링 ({len(all_rgb_values)}개 칸 → 6개 그룹)")
        
        all_rgb_array = np.array(all_rgb_values)
        kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
        kmeans.fit(all_rgb_array)
        
        cluster_centers = kmeans.cluster_centers_
        all_labels = kmeans.labels_
        
        print("K-means 클러스터링 완료!")
        for i, center in enumerate(cluster_centers):
            print(f"  클러스터 {i}: RGB{tuple(center.astype(int))}")
        
        # Phase 3: 클러스터를 기준 색상에 매칭 (헝가리안 알고리즘)
        print("\nPhase 3: 클러스터 → 기준 색상 1:1 매칭")
        
        cluster_to_color = assign_clusters_to_colors(cluster_centers)
        
        print("매칭 결과:")
        for cluster_id in sorted(cluster_to_color.keys()):
            color_name = cluster_to_color[cluster_id]
            center_rgb = cluster_centers[cluster_id].astype(int)
            ref_rgb = REFERENCE_COLORS[color_name].astype(int)
            distance = rgb_distance(cluster_centers[cluster_id], REFERENCE_COLORS[color_name])
            print(f"  클러스터 {cluster_id} RGB{tuple(center_rgb)} → {color_name:7s} (거리: {distance:.1f})")
        
        # Phase 4: 각 면의 색상 결과 생성
        print("\nPhase 4: 결과 생성")
        
        cube_colors = {}
        analysis_results = {}
        label_idx = 0
        
        for img_data in all_images_data:
            face = img_data['face']
            
            # 이 면의 9개 칸에 대한 클러스터 레이블
            image_labels = all_labels[label_idx:label_idx+9]
            label_idx += 9
            
            # 색상 이름으로 변환 (full name → 단일 문자)
            colors_full = [cluster_to_color[label] for label in image_labels]
            colors = [COLOR_LABEL_MAP[c] for c in colors_full]
            
            # 3x3 그리드로 변환
            color_grid = [[colors[r * 3 + c] for c in range(3)] for r in range(3)]
            cube_colors[face] = color_grid
            
            # 16진수 색상으로 변환
            hex_grid = [[COLOR_MAP.get(cell, "#808080") for cell in row] for row in color_grid]
            
            analysis_results[face] = {
                "colors": color_grid,
                "hex_colors": hex_grid,
                "cluster_labels": image_labels.tolist(),
                "status": "success"
            }
            
            print(f"\n{face} 면:")
            for row in color_grid:
                print(f"  {' '.join(row)}")
        
        # 분석 결과 저장 (세션별 디렉토리에)
        result_path = session_dir / "analyzed_colors.json"
        result_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "method": "kmeans_clustering",
            "cluster_centers": cluster_centers.tolist(),
            "cluster_mapping": {str(k): v for k, v in cluster_to_color.items()},
            "cube_colors": cube_colors,
            "analysis_results": analysis_results
        }
        
        if HAS_AIOFILES:
            async with aiofiles.open(result_path, 'w', encoding='utf-8') as f:  # type: ignore
                await f.write(json.dumps(result_data, ensure_ascii=False, indent=2))
        else:
            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(result_data, ensure_ascii=False, indent=2))
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{len(cube_colors)}개 면의 색상 분석이 완료되었습니다 (K-means 클러스터링)",
                "session_id": session_id,
                "data": {
                    "cube_colors": cube_colors,
                    "analysis_results": analysis_results,
                    "cluster_info": {
                        "centers": cluster_centers.tolist(),
                        "mapping": {str(k): v for k, v in cluster_to_color.items()}
                    },
                    "result_file": str(result_path)
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}"
        )