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
import kociemba

# 큐브 해법 모듈
from cube_solver import (
    solve_cube,
    convert_to_frontend_format,
    correct_face_rotations,
    build_dynamic_color_map
)

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

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 기존 세션 복원"""
    print("\n🔄 서버 시작 - 기존 세션 복원 중...")
    
    if not UPLOAD_DIR.exists():
        print("⚠️ 업로드 디렉토리가 없습니다.")
        return
    
    # 모든 세션 디렉토리 스캔
    session_dirs = [d for d in UPLOAD_DIR.iterdir() if d.is_dir()]
    restored_count = 0
    
    for session_dir in session_dirs:
        session_id = session_dir.name
        try:
            # UUID 형식인지 확인
            uuid.UUID(session_id)
            
            # 세션 복원
            if restore_session(session_id):
                restored_count += 1
        except (ValueError, AttributeError):
            # UUID가 아닌 디렉토리는 건너뛰기
            continue
    
    print(f"✅ {restored_count}개의 세션이 복원되었습니다.\n")

def restore_session(session_id: str) -> bool:
    """디스크에서 세션 복원"""
    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        return False
    
    try:
        # 세션 데이터 복원
        SESSIONS[session_id] = {
            "created_at": datetime.fromtimestamp(session_dir.stat().st_ctime),
            "images": {}
        }
        
        # 이미지 메타데이터 복원
        for json_file in session_dir.glob("*.json"):
            # analyzed_colors.json, solution.json 등은 제외
            if json_file.stem in ["analyzed_colors", "solution"]:
                continue
            
            # 메타데이터 파일인지 확인 (파일명이 .jpg.json 형태)
            if not json_file.stem.endswith(".jpg"):
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if "face" in metadata:
                        SESSIONS[session_id]["images"][metadata["face"]] = metadata
            except Exception as e:
                print(f"⚠️ 메타데이터 복원 실패 {json_file}: {e}")
                continue
        
        print(f"✅ 세션 {session_id[:8]}... 복원 완료 ({len(SESSIONS[session_id]['images'])}개 이미지)")
        return True
        
    except Exception as e:
        print(f"❌ 세션 복원 실패 {session_id[:8]}...: {e}")
        return False

def get_session_id(request=None) -> str:
    """요청에서 세션 ID 가져오기 또는 새로 생성"""
    # 헤더에서 세션 ID 확인
    if request and hasattr(request, 'headers'):
        session_id = request.headers.get('X-Session-Id')
        if session_id:
            # 메모리에 세션이 없으면 복원 시도
            if session_id not in SESSIONS:
                if restore_session(session_id):
                    return session_id
            else:
                return session_id
    
    # 새 세션 생성
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "created_at": datetime.now(),
        "images": {}
    }
    print(f"🆕 새 세션 생성: {session_id[:8]}...")
    return session_id

def get_session_upload_dir(session_id: str) -> Path:
    """세션별 업로드 디렉토리 반환"""
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def validate_session(session_id: str, auto_restore: bool = True) -> bool:
    """세션 ID 유효성 확인 (자동 복원 지원)"""
    if session_id in SESSIONS:
        return True
    
    # 자동 복원 시도
    if auto_restore:
        session_dir = UPLOAD_DIR / session_id
        if session_dir.exists():
            return restore_session(session_id)
    
    return False

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
        
        # 세션 유효성 검사 (자동 복원 포함)
        if not validate_session(session_id):
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
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
    세션 ID가 없거나 유효하지 않으면 빈 데이터 반환
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        
        # 세션 ID가 없으면 빈 데이터 반환 (404 대신)
        if not session_id:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "세션 ID가 없습니다.",
                    "session_id": None,
                    "data": {}
                }
            )
        
        # 세션 유효성 검사 (자동 복원 시도)
        if not validate_session(session_id):
            # 유효하지 않은 세션이면 빈 데이터 반환
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "유효하지 않은 세션입니다.",
                    "session_id": session_id,
                    "data": {}
                }
            )
        
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

# ==================== RGB + HSV 이중 클러스터링 기반 색상 분석 (remove_bg.py에서 가져옴) ====================

# 기준 RGB 값 정의
REFERENCE_COLORS_RGB = {
    'white':  np.array([220, 230, 240]),
    'yellow': np.array([180, 220, 130]),
    'orange': np.array([200, 100, 80]),
    'red':    np.array([145, 50, 45]),
    'green':  np.array([55, 180, 110]),
    'blue':   np.array([20, 80, 150])
}

# 기준 HSV 값 정의 (OpenCV 형식: H=0-180, S=0-255, V=0-255)
REFERENCE_COLORS_HSV = {
    'white':  np.array([100, 50, 230]),
    'yellow': np.array([73, 180, 180]),
    'orange': np.array([10, 150, 200]),
    'red':    np.array([2, 180, 140]),
    'green':  np.array([60, 180, 200]),
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
    특정 세션의 업로드된 모든 큐브 이미지를 RGB + HSV 이중 클러스터링으로 분석하여 색상 데이터 추출
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
        
        print(f"\n[세션 {session_id[:8]}...] Phase 1: {len(images_info)}개 이미지 전처리 및 RGB 수집")
        
        for face, metadata in sorted(images_info.items()):
            image_path = session_dir / metadata["saved_filename"]
            
            try:
                # 이미지 전처리 (배경 제거 + Perspective 변환)
                square_array = preprocess_cube_image(image_path)
                
                # 각 칸에서 RGB 추출
                for row in range(3):
                    for col in range(3):
                        rgb, _ = extract_rgb_from_cell(square_array, row, col)
                        all_rgb_values.append(rgb)
                
                all_images_data.append({
                    'face': face,
                    'array': square_array
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
        
        all_rgb_array = np.array(all_rgb_values)
        total_cells = len(all_rgb_array)
        
        print(f"\n총 {total_cells}개 칸의 RGB 데이터 수집 완료")
        
        # Phase 2-A: RGB 클러스터링
        print(f"\nPhase 2-A: RGB 클러스터링 (6개 그룹)")
        
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
        
        # Phase 2-B: HSV 클러스터링
        print(f"\nPhase 2-B: HSV 클러스터링 (6개 그룹)")
        
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
        
        # Phase 3: 앙상블 투표
        print(f"\nPhase 3: 앙상블 투표 (RGB + HSV 종합)")
        
        cube_colors = {}
        analysis_results = {}
        cell_idx = 0
        
        agree_count = 0
        rgb_win_count = 0
        hsv_win_count = 0
        recheck_count = 0
        
        for img_data in all_images_data:
            face = img_data['face']
            
            colors_full = []
            confidences = []
            reasons = []
            
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
                    
                    colors_full.append(final_color)
                    confidences.append(confidence)
                    reasons.append(reason)
                    
                    if reason == 'both_agree':
                        agree_count += 1
                    elif reason == 'hsv_recheck':
                        recheck_count += 1
                    elif reason == 'rgb_wins':
                        rgb_win_count += 1
                    else:
                        hsv_win_count += 1
                    
                    cell_idx += 1
            
            # 색상 이름을 단일 문자로 변환
            colors = [COLOR_LABEL_MAP[c] for c in colors_full]
            
            # 3x3 그리드로 변환
            color_grid = [[colors[r * 3 + c] for c in range(3)] for r in range(3)]
            cube_colors[face] = color_grid
            
            # 16진수 색상으로 변환
            hex_grid = [[COLOR_MAP.get(cell, "#808080") for cell in row] for row in color_grid]
            
            analysis_results[face] = {
                "colors": color_grid,
                "hex_colors": hex_grid,
                "confidences": confidences,
                "reasons": reasons,
                "status": "success"
            }
            
            print(f"\n{face} 면:")
            for r_idx, row in enumerate(color_grid):
                conf_str = " ".join([f"{confidences[r_idx*3+c]:.0%}" for c in range(3)])
                print(f"  {' '.join(row)}  ({conf_str})")
        
        # 통계 출력
        print(f"\n앙상블 통계:")
        print(f"총 칸 수: {total_cells}")
        print(f"RGB-HSV 일치: {agree_count} ({agree_count/total_cells*100:.1f}%)")
        print(f"HSV 재검증: {recheck_count} ({recheck_count/total_cells*100:.1f}%)")
        print(f"RGB 우세: {rgb_win_count} ({rgb_win_count/total_cells*100:.1f}%)")
        print(f"HSV 우세: {hsv_win_count} ({hsv_win_count/total_cells*100:.1f}%)")
        
        # 분석 결과 저장 (세션별 디렉토리에)
        result_path = session_dir / "analyzed_colors.json"
        result_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "method": "rgb_hsv_dual_clustering_ensemble",
            "rgb_cluster_centers": rgb_cluster_centers.tolist(),
            "hsv_cluster_centers": hsv_cluster_centers.tolist(),
            "rgb_cluster_mapping": {str(k): v for k, v in rgb_cluster_to_color.items()},
            "hsv_cluster_mapping": {str(k): v for k, v in hsv_cluster_to_color.items()},
            "ensemble_stats": {
                "total_cells": total_cells,
                "agree_count": agree_count,
                "recheck_count": recheck_count,
                "rgb_win_count": rgb_win_count,
                "hsv_win_count": hsv_win_count
            },
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
                "message": f"{len(cube_colors)}개 면의 색상 분석이 완료되었습니다 (RGB + HSV 이중 클러스터링 앙상블)",
                "session_id": session_id,
                "data": {
                    "cube_colors": cube_colors,
                    "analysis_results": analysis_results,
                    "ensemble_stats": {
                        "total_cells": total_cells,
                        "agree_count": agree_count,
                        "recheck_count": recheck_count,
                        "rgb_win_count": rgb_win_count,
                        "hsv_win_count": hsv_win_count
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

@app.post("/generate-solution")
async def generate_solution(request: Request):
    """
    분석된 큐브 색상으로부터 해법 생성
    
    요청 본문에 cube_colors가 있으면 사용, 없으면 세션의 analyzed_colors.json 사용
    """
    try:
        # 헤더에서 세션 ID 가져오기
        session_id = request.headers.get('X-Session-Id')
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id 헤더가 필요합니다.")
        
        # 세션 유효성 검사
        if not validate_session(session_id):
            raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")
        
        session_dir = get_session_upload_dir(session_id)
        
        # 요청 본문에서 cube_colors 가져오기 시도
        try:
            body = await request.json()
            cube_colors = body.get("cube_colors")
            if cube_colors:
                print(f"\n[세션 {session_id[:8]}...] 요청 본문에서 큐브 색상 사용 (3D 큐브 조작)")
        except:
            cube_colors = None
        
        # 요청 본문에 없으면 세션 파일에서 읽기
        if not cube_colors:
            result_path = session_dir / "analyzed_colors.json"
            
            # 분석 결과 파일 확인
            if not result_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail="큐브 색상 분석 결과를 찾을 수 없습니다. 먼저 /analyze-cube-images를 호출하세요."
                )
            
            # 분석 결과 읽기
            if HAS_AIOFILES:
                async with aiofiles.open(result_path, 'r', encoding='utf-8') as f:  # type: ignore
                    content = await f.read()
            else:
                with open(result_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            analysis_data = json.loads(content)
            cube_colors = analysis_data["cube_colors"]
            print(f"\n[세션 {session_id[:8]}...] 세션 파일에서 큐브 색상 사용 (이미지 분석)")
        
        print(f"\n[세션 {session_id[:8]}...] 큐브 해법 생성 시작")
        print(f"원본 큐브 색상: {cube_colors}")
        
        # 해법 생성
        solution_result = solve_cube(cube_colors)
        
        if not solution_result["success"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "큐브 해법 생성 실패",
                    "error": solution_result.get("error"),
                    "error_type": solution_result.get("error_type")
                }
            )
        
        # 프론트엔드 형식으로 변환
        frontend_cube = convert_to_frontend_format(
            solution_result["corrected_cube"],
            solution_result["color_map"]
        )
        
        # 결과 저장
        solution_path = session_dir / "solution.json"
        solution_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "kociemba_string": solution_result["kociemba_string"],
            "solution": solution_result["solution"],
            "move_count": solution_result["move_count"],
            "moves": solution_result["moves"],
            "color_map": solution_result["color_map"],
            "frontend_cube": frontend_cube
        }
        
        if HAS_AIOFILES:
            async with aiofiles.open(solution_path, 'w', encoding='utf-8') as f:  # type: ignore
                await f.write(json.dumps(solution_data, ensure_ascii=False, indent=2))
        else:
            with open(solution_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(solution_data, ensure_ascii=False, indent=2))
        
        print(f"해법 생성 완료: {solution_result['solution']}")
        print(f"이동 횟수: {solution_result['move_count']}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"큐브 해법이 생성되었습니다 ({solution_result['move_count']}회 이동)",
                "session_id": session_id,
                "data": {
                    "solution": solution_result["solution"],
                    "moves": solution_result["moves"],
                    "move_count": solution_result["move_count"],
                    "kociemba_string": solution_result["kociemba_string"],
                    "color_map": solution_result["color_map"],
                    "frontend_cube": frontend_cube
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
            detail=f"해법 생성 중 오류가 발생했습니다: {str(e)}"
        )