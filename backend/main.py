import os
import io
import uuid
from typing import List, Optional
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

# 최대 파일 크기 (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

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