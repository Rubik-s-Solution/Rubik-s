#!/usr/bin/env python3
"""
Rubik's Cube Image Upload Backend Server
FastAPI 기반 이미지 업로드 서버를 실행합니다.

사용법:
    python run_server.py

또는 uvicorn으로 직접 실행:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """필요한 의존성 패키지들이 설치되어 있는지 확인"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'python-multipart',
        'Pillow',
        'aiofiles'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 필요한 패키지들이 설치되지 않았습니다: {', '.join(missing_packages)}")
        print(f"다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        print(f"\n또는 requirements.txt를 사용하세요:")
        print(f"pip install -r requirements.txt")
        return False
    
    print("✅ 모든 필요한 패키지가 설치되어 있습니다.")
    return True

def create_upload_directory():
    """업로드 디렉토리 생성"""
    upload_dir = Path("uploaded_images")
    upload_dir.mkdir(exist_ok=True)
    print(f"📁 업로드 디렉토리: {upload_dir.absolute()}")

def run_server():
    """FastAPI 서버 실행"""
    try:
        print("🚀 Rubik's Cube Image Upload Server를 시작합니다...")
        print("📡 서버 주소: http://localhost:8000")
        print("📄 API 문서: http://localhost:8000/docs")
        print("🛑 서버를 중지하려면 Ctrl+C를 누르세요")
        print("-" * 50)
        
        # uvicorn으로 서버 실행
        result = subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=Path(__file__).parent)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n🛑 서버가 중지되었습니다.")
        return 0
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {e}")
        return 1

def main():
    """메인 함수"""
    print("🎲 Rubik's Cube Image Upload Backend")
    print("=" * 40)
    
    # 의존성 확인
    if not check_dependencies():
        return 1
    
    # 업로드 디렉토리 생성
    create_upload_directory()
    
    # 서버 실행
    return run_server()

if __name__ == "__main__":
    sys.exit(main())