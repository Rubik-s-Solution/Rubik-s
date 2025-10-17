import os
from rembg import remove
from PIL import Image
import glob

def remove_background_from_folder(input_folder='cube_img', output_folder='output_no_bg'):
    """
    특정 폴더의 모든 이미지에서 배경을 제거합니다.
    
    Parameters:
    - input_folder: 원본 이미지가 있는 폴더 경로
    - output_folder: 배경이 제거된 이미지를 저장할 폴더 경로
    """
    
    # 출력 폴더가 없으면 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 지원되는 이미지 확장자
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
    
    # 모든 이미지 파일 경로 수집
    image_files = []
    for extension in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_folder, extension)))
    
    if not image_files:
        print(f"'{input_folder}' 폴더에서 이미지를 찾을 수 없습니다.")
        return
    
    print(f"총 {len(image_files)}개의 이미지를 처리합니다...")
    
    # 각 이미지 처리
    for idx, image_path in enumerate(image_files, 1):
        try:
            # 파일명 추출
            filename = os.path.basename(image_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            print(f"처리 중 ({idx}/{len(image_files)}): {filename}")
            
            # 이미지 열기
            input_image = Image.open(image_path)
            
            # 배경 제거
            output_image = remove(input_image)
            
            # PNG로 저장 (투명 배경 지원)
            output_path = os.path.join(output_folder, f"{name_without_ext}_no_bg.png")
            output_image.save(output_path, 'PNG')
            
            print(f"  ✓ 저장 완료: {output_path}")
            
        except Exception as e:
            print(f"  ✗ 오류 발생 ({filename}): {str(e)}")
            continue
    
    print(f"\n배경 제거 완료! 결과는 '{output_folder}' 폴더에 저장되었습니다.")

def remove_background_single(image_path, output_path=None):
    """
    단일 이미지의 배경을 제거합니다.
    
    Parameters:
    - image_path: 원본 이미지 경로
    - output_path: 저장할 경로 (None이면 자동 생성)
    """
    try:
        # 이미지 열기
        input_image = Image.open(image_path)
        
        # 배경 제거
        output_image = remove(input_image)
        
        # 출력 경로 설정
        if output_path is None:
            name_without_ext = os.path.splitext(image_path)[0]
            output_path = f"{name_without_ext}_no_bg.png"
        
        # 저장
        output_image.save(output_path, 'PNG')
        print(f"배경 제거 완료: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return None

# 고급 옵션을 사용한 배경 제거
def remove_background_advanced(input_folder='cube_img', output_folder='output_no_bg', 
                              model='u2net', alpha_matting=True):
    """
    고급 옵션을 사용한 배경 제거
    
    Parameters:
    - input_folder: 입력 폴더
    - output_folder: 출력 폴더
    - model: 사용할 모델 ('u2net', 'u2netp', 'u2net_human_seg', 'u2net_cloth_seg')
    - alpha_matting: 더 정교한 가장자리 처리 사용 여부
    """
    from rembg import new_session
    
    # 세션 생성
    session = new_session(model)
    
    # 출력 폴더 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 이미지 파일 목록
    image_extensions = ['*.png', '*.jpg', '*.jpeg']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(input_folder, ext)))
    
    print(f"모델 '{model}'을 사용하여 {len(image_files)}개 이미지 처리...")
    
    for idx, image_path in enumerate(image_files, 1):
        try:
            filename = os.path.basename(image_path)
            print(f"처리 중 ({idx}/{len(image_files)}): {filename}")
            
            # 이미지 열기
            input_image = Image.open(image_path)
            
            # 배경 제거 (세션 사용)
            if alpha_matting:
                output_image = remove(input_image, session=session, alpha_matting=True, 
                                    alpha_matting_foreground_threshold=240,
                                    alpha_matting_background_threshold=50)
            else:
                output_image = remove(input_image, session=session)
            
            # 저장
            name_without_ext = os.path.splitext(filename)[0]
            output_path = os.path.join(output_folder, f"{name_without_ext}_no_bg.png")
            output_image.save(output_path, 'PNG')
            
            print(f"  ✓ 완료: {output_path}")
            
        except Exception as e:
            print(f"  ✗ 오류: {str(e)}")

if __name__ == "__main__":
    # 기본 사용법: cube_img 폴더의 모든 이미지 배경 제거
    remove_background_from_folder('cube_img', 'output_no_bg')
    
    # 단일 이미지 처리 예시
    # remove_background_single('cube_img/sample.jpg')
    
    # 고급 옵션 사용 예시 (더 정교한 결과)
    # remove_background_advanced('cube_img', 'output_advanced', model='u2net', alpha_matting=True)