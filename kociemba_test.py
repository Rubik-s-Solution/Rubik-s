# -*- coding: utf-8 -*-
"""
cube_debug/cube_colors.json, cube_debug/cube_hsv.json 을 사용해
URFDLB 상태 문자열을 만들고 kociemba로 해법을 출력한다.

우선순위:
1) --map 제공 시: 사용자가 지정한 face->color 매핑 사용
2) 자동 매핑: cube_colors.json의 '센터색'으로 color->face 생성
3) 자동 실패 시: cube_hsv.json의 6개 센터 HSV에 '최근접'으로 모든 스티커를 할당
"""
from __future__ import annotations
import json, argparse
from pathlib import Path
from collections import Counter
import math

import kociemba

ORDER = ["U","R","F","D","L","B"]  # Kociemba 요구 입력 순서(URFDLB)

# -------------------- IO --------------------
def load_json(p: str):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_files():
    cc = Path("cube_debug") / "cube_colors.json"
    hh = Path("cube_debug") / "cube_hsv.json"
    if not cc.exists():
        raise SystemExit("cube_debug/cube_colors.json 이 없습니다. 먼저 test.py를 실행해 전개도를 추출하세요.")
    return str(cc), (str(hh) if hh.exists() else None)

# -------------------- 통계/검증 --------------------
def color_counts(faces: dict) -> dict:
    cnt = Counter()
    for face in faces.values():
        for row in face:
            cnt.update(row)
    return dict(cnt)

def check_urfdlb_counts(state: str) -> dict:
    c = Counter(state)
    return {f: c.get(f, 0) for f in ORDER}

# -------------------- 방법 1: 사용자 수동 매핑 --------------------
def parse_map_arg(map_str: str) -> dict:
    """
    "U=w,R=b,F=r,D=y,L=g,B=o" -> color->face 로 뒤집어서 반환
    """
    m = {}
    for pair in map_str.split(","):
        k, v = pair.split("=")
        k, v = k.strip().upper(), v.strip().lower()
        if k not in ORDER: raise ValueError(f"면 문자가 이상함: {k} (URFDLB만 가능)")
        if v not in list("woyrgb"): raise ValueError(f"색 문자가 이상함: {v} (w,o,y,r,g,b)")
        m[k] = v
    if set(m.keys()) != set(ORDER):
        raise ValueError("모든 면(U,R,F,D,L,B)을 지정해야 합니다.")
    # face->color -> color->face
    c2f = {v: k for k, v in m.items()}
    if len(c2f) != 6:
        raise ValueError("수동 매핑에 중복 색이 있습니다.")
    return c2f

def faces_to_state_by_color_map(faces: dict, color2face: dict) -> str:
    chars = []
    for face in ORDER:
        for r in range(3):
            for c in range(3):
                col = faces[face][r][c]
                if col not in color2face:
                    raise ValueError(f"매핑에 없는 색 발견: {col}")
                chars.append(color2face[col])
    state = "".join(chars)
    counts = check_urfdlb_counts(state)
    for f in ORDER:
        if counts[f] != 9:
            raise ValueError(f"면 '{f}' 개수 {counts[f]}개 (정상 9개). 매핑/인식 점검 필요.")
    return state

# -------------------- 방법 2: 자동 매핑(센터 색) --------------------
def auto_color2face_map(faces: dict) -> dict:
    c2f = {}
    for face in ORDER:
        center = faces[face][1][1]
        if center in c2f:
            raise ValueError(f"센터색 중복: '{center}' (이미 {c2f[center]}에 사용됨)")
        c2f[center] = face
    if len(c2f) != 6:
        raise ValueError(f"센터색 6종이 아님: {c2f}")
    return c2f

# -------------------- 방법 3: HSV 최근접(센터 6개) --------------------
def hsv_dist(a, b, w_h=2.0, w_s=1.0, w_v=1.0) -> float:
    ha, sa, va = a; hb, sb, vb = b
    dh = min(abs(ha-hb), 180-abs(ha-hb))  # Hue 원형 거리
    return w_h*dh + w_s*abs(sa-sb) + w_v*abs(va-vb)

def build_state_from_centers_hsv(faces_hsv: dict) -> str:
    # 6개 센터 HSV 수집
    centers = {face: faces_hsv[face][1][1] for face in ORDER}
    # 최근접 센터에 할당
    out = []
    for face in ORDER:
        for r in range(3):
            for c in range(3):
                hsv = faces_hsv[face][r][c]
                best = min(centers.keys(), key=lambda f: hsv_dist(hsv, centers[f]))
                out.append(best)
    state = "".join(out)
    counts = check_urfdlb_counts(state)
    for f in ORDER:
        if counts[f] != 9:
            raise ValueError(f"[HSV최근접] 면 '{f}' 개수 {counts[f]}개 (정상 9개). 촬영/인식 재확인 필요.")
    return state

# -------------------- 메인 --------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", help='수동 매핑 예: U=w,R=b,F=r,D=y,L=g,B=o')
    ap.add_argument("--colors", default=None, help="colors.json 경로(기본: cube_debug/cube_colors.json)")
    ap.add_argument("--hsv", default=None, help="hsv.json 경로(기본: cube_debug/cube_hsv.json 있으면 사용)")
    args = ap.parse_args()

    # 파일 확보
    default_colors, default_hsv = ensure_files()
    colors_path = args.colors or default_colors
    hsv_path = args.hsv or default_hsv

    faces = load_json(colors_path)
    print("[색 카운트]", color_counts(faces))

    # 1) 수동 매핑 우선
    if args.map:
        c2f = parse_map_arg(args.map)
        print("[수동 매핑(color->face)]", c2f)
        state = faces_to_state_by_color_map(faces, c2f)
    else:
        # 2) 자동 매핑(센터 색)
        try:
            c2f = auto_color2face_map(faces)
            print("[자동 매핑(color->face)]", c2f)
            state = faces_to_state_by_color_map(faces, c2f)
        except Exception as e_auto:
            # 3) HSV 최근접(센터 6개)
            if not hsv_path:
                raise SystemExit(f"자동 매핑 실패({e_auto}). cube_hsv.json이 없어 HSV 최근접도 못합니다. "
                                 f"수동 매핑(--map) 또는 test.py 재실행 필요.")
            faces_hsv = load_json(hsv_path)
            print("[자동 매핑 실패] -> HSV 최근접으로 전환:", e_auto)
            state = build_state_from_centers_hsv(faces_hsv)

    counts = check_urfdlb_counts(state)
    print("[면별 스티커 개수]", counts)
    print("[Kociemba 입력(URFDLB)]", state)

    # 솔버
    solution = kociemba.solve(state)
    print("✅ 해결 수열:", solution)

if __name__ == "__main__":
    main()
