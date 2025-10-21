"""
루빅스 큐브 해법 생성 및 변환 모듈
"""
import kociemba
import numpy as np
from typing import Dict, List, Tuple

# 면 회전 보정 매핑 (일단 모두 0으로 테스트)
FACE_ROTATION_CORRECTION = {
    'U': 0,    # 윗면 - 정상
    'F': 0,    # 정면 - 정상
    'D': 0,    # 밑면 - 테스트
    'L': 0,    # 왼면 - 테스트
    'R': 0,    # 오른면 - 테스트
    'B': 0,    # 뒷면 - 테스트
}

def rotate_face_90_clockwise(face_grid):
    """3x3 그리드를 시계방향 90도 회전"""
    return [
        [face_grid[2][0], face_grid[1][0], face_grid[0][0]],
        [face_grid[2][1], face_grid[1][1], face_grid[0][1]],
        [face_grid[2][2], face_grid[1][2], face_grid[0][2]]
    ]

def rotate_face_180(face_grid):
    """3x3 그리드를 180도 회전"""
    return [
        [face_grid[2][2], face_grid[2][1], face_grid[2][0]],
        [face_grid[1][2], face_grid[1][1], face_grid[1][0]],
        [face_grid[0][2], face_grid[0][1], face_grid[0][0]]
    ]

def rotate_face_270_clockwise(face_grid):
    """3x3 그리드를 반시계방향 90도 회전 (시계방향 270도)"""
    return [
        [face_grid[0][2], face_grid[1][2], face_grid[2][2]],
        [face_grid[0][1], face_grid[1][1], face_grid[2][1]],
        [face_grid[0][0], face_grid[1][0], face_grid[2][0]]
    ]

def apply_face_rotation(face_grid, rotation_angle):
    """주어진 각도만큼 면 회전"""
    if rotation_angle == 0:
        return face_grid
    elif rotation_angle == 90:
        return rotate_face_90_clockwise(face_grid)
    elif rotation_angle == 180:
        return rotate_face_180(face_grid)
    elif rotation_angle == 270:
        return rotate_face_270_clockwise(face_grid)
    else:
        raise ValueError(f"지원하지 않는 회전 각도: {rotation_angle}")

def correct_face_rotations(cube_colors: Dict[str, List[List[str]]]) -> Dict[str, List[List[str]]]:
    """
    각 면의 회전 보정 적용
    
    Args:
        cube_colors: {face: [[color, ...], ...]} 형식의 큐브 색상 데이터
    
    Returns:
        회전 보정이 적용된 큐브 색상 데이터
    """
    corrected = {}
    for face, grid in cube_colors.items():
        rotation = FACE_ROTATION_CORRECTION.get(face, 0)
        corrected[face] = apply_face_rotation(grid, rotation)
    
    return corrected

def build_dynamic_color_map(cube_colors: Dict[str, List[List[str]]]) -> Dict[str, str]:
    """
    중심 색상을 기준으로 동적 color_map 생성
    
    각 면의 중심 색상(5번 위치)이 그 면의 실제 색상을 나타냄
    
    Args:
        cube_colors: 회전 보정된 큐브 색상 데이터
    
    Returns:
        {"색상문자": "면문자"} 매핑 딕셔너리
        예: {"w": "U", "y": "D", "r": "R", "o": "L", "g": "F", "b": "B"}
    """
    color_map = {}
    
    # 각 면의 중심 색상 추출 (1-indexed로 5번 = 0-indexed로 [1][1])
    print("  각 면의 중심 색상:")
    for face, grid in cube_colors.items():
        center_color = grid[1][1]  # 중심 위치
        print(f"    {face} 면 중심: '{center_color}'")
        
        # 중복 체크
        if center_color in color_map:
            raise ValueError(f"중복된 중심 색상 발견: '{center_color}'가 {color_map[center_color]}면과 {face}면에 모두 존재")
        
        color_map[center_color] = face
    
    print(f"  최종 color_map: {color_map}")
    
    # 6개 색상이 모두 있는지 확인
    if len(color_map) != 6:
        raise ValueError(f"색상 개수 오류: {len(color_map)}개 (6개여야 함)")
    
    return color_map

def cube_to_kociemba_string(cube_colors: Dict[str, List[List[str]]], color_map: Dict[str, str]) -> str:
    """
    큐브 색상 데이터를 Kociemba 형식 문자열로 변환
    
    Kociemba 순서: U(위) R(오른쪽) F(앞) D(아래) L(왼쪽) B(뒤)
    각 면은 1-9번 순서 (왼쪽 위부터 오른쪽 아래까지)
    
    Args:
        cube_colors: 회전 보정된 큐브 색상 데이터
        color_map: 색상 → 면 매핑
    
    Returns:
        Kociemba 형식 문자열 (54자)
        예: "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    """
    kociemba_order = ['U', 'R', 'F', 'D', 'L', 'B']
    kociemba_string = ""
    
    print("  Kociemba 문자열 생성 과정:")
    for face_char in kociemba_order:
        if face_char not in cube_colors:
            raise ValueError(f"면 {face_char}의 색상 데이터가 없습니다.")
        
        grid = cube_colors[face_char]
        face_string = ""
        
        # 3x3 그리드를 순서대로 읽기
        for row in grid:
            for color_char in row:
                # 색상 문자를 면 문자로 변환
                face_name = color_map.get(color_char)
                if not face_name:
                    raise ValueError(f"알 수 없는 색상: {color_char}")
                face_string += face_name
        
        print(f"    {face_char} 면: {face_string} (중심={grid[1][1]} → {color_map[grid[1][1]]})")
        kociemba_string += face_string
    
    return kociemba_string

def solve_cube(cube_colors: Dict[str, List[List[str]]]) -> Dict:
    """
    루빅스 큐브 해법 생성
    
    Args:
        cube_colors: 원본 큐브 색상 데이터 (K-means 분석 결과)
    
    Returns:
        {
            "success": bool,
            "kociemba_string": str,  # Kociemba 입력 문자열
            "solution": str,         # 해법 (예: "D R2 F2 D' L2 ...")
            "move_count": int,       # 이동 횟수
            "color_map": dict,       # 사용된 color_map
            "corrected_cube": dict   # 회전 보정된 큐브 데이터
        }
    """
    try:
        # 0. 원본 큐브 데이터 출력
        print("\n=== 큐브 해법 생성 시작 ===")
        print("0. 원본 큐브 데이터 (회전 보정 전):")
        for face in ['U', 'R', 'F', 'D', 'L', 'B']:
            if face in cube_colors:
                grid = cube_colors[face]
                print(f"  {face} 면: {grid[0]} {grid[1]} {grid[2]} (중심={grid[1][1]})")
        
        # 1. 면 회전 보정
        print("\n1. 면 회전 보정 적용...")
        corrected_cube = correct_face_rotations(cube_colors)
        print("  회전 보정 완료")
        
        print("\n1-1. 회전 보정 후 각 면 상태:")
        for face in ['U', 'R', 'F', 'D', 'L', 'B']:
            if face in corrected_cube:
                grid = corrected_cube[face]
                print(f"  {face} 면: {grid[0]} {grid[1]} {grid[2]} (중심={grid[1][1]})")
        
        # 2. 동적 color_map 생성
        print("2. 동적 color_map 생성...")
        color_map = build_dynamic_color_map(corrected_cube)
        
        # 3. Kociemba 문자열 생성
        print("3. Kociemba 문자열 생성...")
        kociemba_string = cube_to_kociemba_string(corrected_cube, color_map)
        print(f"Kociemba 입력: {kociemba_string}")
        
        # 4. 큐브 검증
        print("4. 큐브 문자열 검증...")
        if len(kociemba_string) != 54:
            raise ValueError(f"잘못된 큐브 문자열 길이: {len(kociemba_string)} (54자여야 함)")
        
        # 각 면이 정확히 9개씩 있는지 확인
        face_counts = {}
        for face in ['U', 'R', 'F', 'D', 'L', 'B']:
            count = kociemba_string.count(face)
            face_counts[face] = count
            if count != 9:
                raise ValueError(f"면 {face}가 {count}개 발견됨 (9개여야 함)")
        
        print(f"  면 개수 검증 통과: {face_counts}")
        
        # 5. Kociemba 알고리즘으로 해법 생성
        print("5. Kociemba 알고리즘으로 해법 생성...")
        print(f"  입력 문자열: {kociemba_string}")
        
        # 각 면의 색상 분포 확인
        print("\n6. 각 면의 색상 분포 분석:")
        for face_name in ['U', 'R', 'F', 'D', 'L', 'B']:
            if face_name in corrected_cube:
                grid = corrected_cube[face_name]
                center_color = grid[1][1]
                
                # 해당 면의 색상 카운트
                face_flat = [cell for row in grid for cell in row]
                center_count = face_flat.count(center_color)
                
                print(f"  {face_name} 면 (중심색={center_color}): 중심색이 {center_count}/9개")
                print(f"    전체 색상 분포: {dict((color, face_flat.count(color)) for color in set(face_flat))}")
                
                if center_count < 4:
                    print(f"    ⚠️ 경고: {face_name} 면에 중심색이 너무 적습니다! (정상: 5개 이상)")
        
        try:
            solution = kociemba.solve(kociemba_string)
            moves = solution.split()
            
            print(f"\n  ✅ 해법 생성 완료!")
            print(f"  해법: {solution}")
            print(f"  이동 횟수: {len(moves)}")
        except Exception as ke:
            print(f"\n  ❌ Kociemba 오류: {ke}")
            print(f"\n💡 문제 해결 방법:")
            print(f"  1. 큐브 사진이 올바른지 확인하세요 (각 면을 정확히 촬영)")
            print(f"  2. 조명이 일정하고 색상이 선명한지 확인하세요")
            print(f"  3. 각 면의 중심 색상이 해당 면에 충분히 있는지 확인하세요")
            print(f"  4. 실제 큐브가 뒤섞인 상태인지 확인하세요 (조립 오류가 아닌지)")
            raise ValueError(f"Kociemba 해법 생성 실패: {str(ke)}. 큐브 상태가 올바르지 않을 수 있습니다.")
        
        return {
            "success": True,
            "kociemba_string": kociemba_string,
            "solution": solution,
            "move_count": len(moves),
            "moves": moves,
            "color_map": color_map,
            "corrected_cube": corrected_cube
        }
        
    except ValueError as e:
        print(f"큐브 검증 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "validation_error"
        }
    except Exception as e:
        print(f"해법 생성 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "solver_error"
        }

def convert_to_frontend_format(cube_colors: Dict[str, List[List[str]]], color_map: Dict[str, str]) -> Dict:
    """
    백엔드 큐브 데이터를 프론트엔드 형식으로 변환
    
    프론트엔드 순서: U1-U9, R1-R9, F1-F9, D1-D9, L1-L9, B1-B9
    
    Args:
        cube_colors: 회전 보정된 큐브 색상 데이터
        color_map: 색상 → 면 매핑
    
    Returns:
        {
            "U1": "U", "U2": "U", ...,
            "R1": "R", "R2": "R", ...,
            ...
        }
    """
    frontend_cube = {}
    face_order = ['U', 'R', 'F', 'D', 'L', 'B']
    
    for face in face_order:
        if face not in cube_colors:
            continue
        
        grid = cube_colors[face]
        position = 1
        
        for row in grid:
            for color_char in row:
                face_name = color_map.get(color_char, color_char)
                frontend_cube[f"{face}{position}"] = face_name
                position += 1
    
    return frontend_cube
