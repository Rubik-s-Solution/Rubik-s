import os
import io
import uuid
import sys
import subprocess
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
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

app = FastAPI(title="Rubik's Cube Image API", version="1.0.0")

# CORS 설정 (프론트엔드와 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드된 이미지를 저장할 디렉토리 설정
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# 정적 파일 서빙 (업로드된 이미지에 접근하기 위해)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

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
            "upload": "/upload-image",
            "images": "/images/{filename}",
            "cube_images": "/cube-images",
            "health": "/health"
        }
    }

@app.post("/upload-image")
async def upload_image(
    face: str = Form(..., description="큐브 면 (U, D, F, B, L, R)"),
    file: UploadFile = File(..., description="업로드할 이미지 파일")
):
    """
    큐브의 특정 면에 이미지 업로드
    """
    try:
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
        
        # 고유한 파일명 생성 (파일명이 None이 아님을 이미 확인했음)
        if file.filename is None:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{face}_{uuid.uuid4().hex}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # 파일 저장 (aiofiles가 없는 경우 동기 방식 사용)
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
            "image_url": f"/images/{unique_filename}"
        }
        
        # 메타데이터 파일 저장
        metadata_path = UPLOAD_DIR / f"{unique_filename}.json"
        if HAS_AIOFILES:
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:  # type: ignore
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
        else:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{face} 면에 이미지가 성공적으로 업로드되었습니다.",
                "data": metadata
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
async def get_cube_images():
    """
    업로드된 모든 큐브 이미지 정보 조회
    """
    try:
        images_info = {}
        
        # 메타데이터 파일들을 읽어서 정보 수집
        for metadata_file in UPLOAD_DIR.glob("*.json"):
            try:
                if HAS_AIOFILES:
                    async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:  # type: ignore
                        content = await f.read()
                else:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                metadata = json.loads(content)
                face = metadata.get("face")
                if face:
                    images_info[face] = metadata
            except Exception as e:
                print(f"메타데이터 파일 읽기 실패 {metadata_file}: {e}")
                continue
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "큐브 이미지 정보를 성공적으로 조회했습니다.",
                "data": images_info
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )

@app.delete("/cube-images/{face}")
async def delete_cube_image(face: str):
    """
    특정 면의 이미지 삭제
    """
    try:
        validate_cube_face(face)
        
        deleted_files = []
        
        # 해당 면의 이미지와 메타데이터 파일 찾기 및 삭제
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                # 메타데이터 파일인 경우
                if file_path.suffix == '.json':
                    try:
                        if HAS_AIOFILES:
                            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:  # type: ignore
                                content = await f.read()
                        else:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                        metadata = json.loads(content)
                        if metadata.get("face") == face:
                                # 해당 이미지 파일도 삭제
                                image_file = UPLOAD_DIR / metadata.get("saved_filename", "")
                                if image_file.exists():
                                    os.remove(image_file)
                                    deleted_files.append(str(image_file))
                                
                                # 메타데이터 파일 삭제
                                os.remove(file_path)
                                deleted_files.append(str(file_path))
                                break
                    except Exception as e:
                        print(f"메타데이터 파일 처리 실패 {file_path}: {e}")
                        continue
        
        if deleted_files:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"{face} 면의 이미지가 성공적으로 삭제되었습니다.",
                    "deleted_files": deleted_files
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"{face} 면에 업로드된 이미지가 없습니다."
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

# ==================== 색상 분석 함수들 (test.py에서 가져옴) ====================

def order_quad(pts):
    """사각형 4점을 TL, TR, BR, BL 순서로 정렬"""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    out = np.zeros((4, 2), dtype=np.float32)
    out[0] = pts[np.argmin(s)]  # TL
    out[2] = pts[np.argmax(s)]  # BR
    out[1] = pts[np.argmin(d)]  # TR
    out[3] = pts[np.argmax(d)]  # BL
    return out

def detect_face_quad(bgr):
    """면 외곽 검출"""
    h, w = bgr.shape[:2]
    scale = 1400 / max(h, w) if max(h, w) > 1400 else 1.0
    small = cv2.resize(bgr, (int(w*scale), int(h*scale)),
                       interpolation=cv2.INTER_AREA) if scale != 1.0 else bgr.copy()

    hs, ws = small.shape[:2]

    # 색/화이트 마스크 경로
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)
    mask_color = ((S > 60) & (V > 80)).astype(np.uint8) * 255
    mask_white = ((S < 55) & (V > 190)).astype(np.uint8) * 255
    mask = cv2.bitwise_or(mask_color, mask_white)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, 2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < 0.0006 * hs * ws or a > 0.35 * hs * ws:
            continue
        (cx, cy), (rw, rh), _ = cv2.minAreaRect(c)
        if min(rw, rh) == 0:
            continue
        if max(rw, rh) / min(rw, rh) > 2.0:
            continue
        cands.append((a, c))

    if cands:
        cands = sorted(cands, key=lambda x: x[0], reverse=True)[:12]
        pts = np.vstack([c.reshape(-1, 2) for _, c in cands]).astype(np.float32)
        hull = cv2.convexHull(pts)
        peri = cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
        if len(approx) != 4:
            rect = cv2.minAreaRect(hull)
            box = cv2.boxPoints(rect)
            approx = box.reshape(-1, 1, 2).astype(np.float32)
        quad = (approx.reshape(-1, 2) * (1 / scale)).astype(np.float32)
        return order_quad(quad)

    # 에지 기반 보조
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), 1)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = -1
    for c in cnts:
        a = cv2.contourArea(c)
        if a < 0.002 * hs * ws:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        rect = approx.reshape(-1, 2)
        x, y, w2, h2 = cv2.boundingRect(rect)
        ar = w2 / h2 if h2 > 0 else 0
        if 0.6 < ar < 1.4:
            score = a
            if score > best_score:
                best_score = score
                best = rect.astype(np.float32)

    if best is not None:
        quad = (best * (1 / scale)).astype(np.float32)
        return order_quad(quad)

    return None

def classify_face_adaptive(hsv_list):
    """적응형 색상 분류"""
    Hs = np.array([h for h, _, _ in hsv_list], dtype=float)
    Ss = np.array([s for _, s, _ in hsv_list], dtype=float)
    Vs = np.array([v for _, _, v in hsv_list], dtype=float)

    s_thr = np.percentile(Ss, 30) + 10
    v_thr = max(np.percentile(Vs, 75) - 5, 165)

    labels = ["?"] * 9
    white_cand = (Ss < s_thr) & (Vs > v_thr)

    for i, (h, s, v) in enumerate(hsv_list):
        if 90 <= h <= 135:  # blue
            if v > 80:
                white_cand[i] = False
        if 37 <= h <= 90:  # green
            if v > 80:
                white_cand[i] = False
        if (h <= 10 or h >= 170) or (10 < h < 40):
            if s > 40:
                white_cand[i] = False

    for i in np.where(white_cand)[0]:
        labels[i] = "w"

    def hue2label(h, s, v):
        if 10 < h <= 25 and s > 45 and v > 70:
            return "o"
        if 25 < h <= 37 and s > 45 and v > 70:
            return "y"
        if 37 < h <= 90 and s > 35 and v > 60:
            return "g"
        if 90 < h <= 135 and s > 30 and v > 60:
            return "b"
        if (h <= 10 or h >= 170) and s > 35 and v > 55:
            return "r"
        return "?"

    for i in range(9):
        if labels[i] == "?":
            labels[i] = hue2label(*hsv_list[i])

    canon = {"r": 0, "o": 17, "y": 31, "g": 60, "b": 110}
    if labels[4] in canon:
        c = labels[4]
        for i in range(9):
            if labels[i] == "?":
                labels[i] = c if Ss[i] > (s_thr * 0.8) else "w"
    else:
        for i in range(9):
            if labels[i] == "?":
                h = Hs[i]
                best = min(canon.items(), key=lambda kv: min(abs(h - kv[1]), 180 - abs(h - kv[1])))[0]
                labels[i] = best
    return labels

def robust_cell_hsv(hsv_img, x1, y1, x2, y2, subgrid=3, subclip=0.6):
    """셀 내부 멀티샘플 HSV"""
    H, W = hsv_img.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(W, x2)
    y2 = min(H, y2)
    gh = (y2 - y1) / subgrid
    gw = (x2 - x1) / subgrid

    h_list, s_list, v_list = [], [], []
    min_valid = max(3, int(0.4 * subgrid * subgrid))

    for r in range(subgrid):
        for c in range(subgrid):
            sy1 = int(y1 + r * gh)
            sy2 = int(y1 + (r + 1) * gh)
            sx1 = int(x1 + c * gw)
            sx2 = int(x1 + (c + 1) * gw)
            my = int((1 - subclip) * (sy2 - sy1) / 2.0)
            mx = int((1 - subclip) * (sx2 - sx1) / 2.0)
            cy1, cy2 = sy1 + my, sy2 - my
            cx1, cx2 = sx1 + mx, sx2 - mx
            if cy2 <= cy1 or cx2 <= cx1:
                continue

            patch = hsv_img[cy1:cy2, cx1:cx2]
            Hm = float(np.median(patch[:, :, 0]))
            Sm = float(np.median(patch[:, :, 1]))
            Vm = float(np.median(patch[:, :, 2]))

            is_color_ok = (Sm > 25 and Vm > 50)
            is_white_ok = (Sm < 35 and Vm > 160)

            if is_color_ok or is_white_ok:
                h_list.append(Hm)
                s_list.append(Sm)
                v_list.append(Vm)

    if len(h_list) >= min_valid:
        return float(np.median(h_list)), float(np.median(s_list)), float(np.median(v_list))

    # 폴백: 셀 중앙 전체 패치
    patch = hsv_img[y1:y2, x1:x2]
    return float(np.median(patch[:, :, 0])), float(np.median(patch[:, :, 1])), float(np.median(patch[:, :, 2]))

def analyze_face_colors(image_path: Path, size=300, patch_ratio=0.50, subgrid=3, subclip=0.6):
    """단일 이미지에서 3x3 색상 추출"""
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    quad = detect_face_quad(bgr)
    if quad is None:
        raise RuntimeError(f"면 외곽 검출 실패: {image_path}")

    dst = np.float32([[0, 0], [size - 1, 0], [size - 1, size - 1], [0, size - 1]])
    M = cv2.getPerspectiveTransform(quad, dst)
    warped = cv2.warpPerspective(bgr, M, (size, size))
    hsv_img = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)

    h_step = size // 3
    w_step = size // 3
    hsv_list, boxes = [], []

    for r in range(3):
        for c in range(3):
            y1, y2 = r * h_step, (r + 1) * h_step
            x1, x2 = c * w_step, (c + 1) * w_step
            my = int((1 - patch_ratio) * (y2 - y1) / 2.0)
            mx = int((1 - patch_ratio) * (x2 - x1) / 2.0)
            cy1, cy2 = y1 + my, y2 - my
            cx1, cx2 = x1 + mx, x2 - mx

            hm, sm, vm = robust_cell_hsv(hsv_img, cx1, cy1, cx2, cy2, subgrid=subgrid, subclip=subclip)
            hsv_list.append((hm, sm, vm))
            boxes.append((cx1, cy1, cx2, cy2))

    labels = classify_face_adaptive(hsv_list)
    grid = [[labels[r * 3 + c] for c in range(3)] for r in range(3)]

    return grid

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
async def analyze_cube_images():
    """
    업로드된 모든 큐브 이미지를 분석하여 색상 데이터 추출
    """
    try:
        # 업로드된 이미지 정보 가져오기
        images_info = {}
        for metadata_file in UPLOAD_DIR.glob("*.json"):
            try:
                if HAS_AIOFILES:
                    async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:  # type: ignore
                        content = await f.read()
                else:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                metadata = json.loads(content)
                face = metadata.get("face")
                if face:
                    images_info[face] = metadata
            except Exception as e:
                print(f"메타데이터 파일 읽기 실패 {metadata_file}: {e}")
                continue
        
        if not images_info:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "분석할 이미지가 없습니다. 먼저 이미지를 업로드하세요."
                }
            )
        
        # 각 면의 색상 분석
        cube_colors = {}
        analysis_results = {}
        
        for face, metadata in images_info.items():
            image_path = UPLOAD_DIR / metadata["saved_filename"]
            
            try:
                # 색상 분석
                color_grid = analyze_face_colors(image_path)
                cube_colors[face] = color_grid
                
                # 16진수 색상으로 변환
                hex_grid = [[COLOR_MAP.get(cell, "#808080") for cell in row] for row in color_grid]
                
                analysis_results[face] = {
                    "colors": color_grid,
                    "hex_colors": hex_grid,
                    "status": "success"
                }
                
            except Exception as e:
                analysis_results[face] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # 분석 결과 저장
        result_path = UPLOAD_DIR / "analyzed_colors.json"
        result_data = {
            "timestamp": datetime.now().isoformat(),
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
                "message": f"{len(cube_colors)}개 면의 색상 분석이 완료되었습니다.",
                "data": {
                    "cube_colors": cube_colors,
                    "analysis_results": analysis_results,
                    "result_file": str(result_path)
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}"
        )