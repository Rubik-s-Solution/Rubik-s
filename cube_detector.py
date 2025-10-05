# cube_face_reader.py
# 스티커 9개를 검출하되, 같은 평면의 3x3 격자만 선택
import cv2, numpy as np, json, glob
from pathlib import Path
from typing import List, Tuple

IN_DIR  = Path("uploaded_images")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def order_quad(pts: np.ndarray) -> np.ndarray:
    pts = np.array(pts, dtype=np.float32).reshape(-1,2)
    s = pts.sum(1); d = np.diff(pts, axis=1).reshape(-1)
    out = np.zeros((4,2), np.float32)
    out[0] = pts[np.argmin(s)]  # TL
    out[2] = pts[np.argmax(s)]  # BR
    out[1] = pts[np.argmin(d)]  # TR
    out[3] = pts[np.argmax(d)]  # BL
    return out

def draw_rot_rect(mask: np.ndarray, rr, color=255):
    box = cv2.boxPoints(rr).astype(np.int32)
    cv2.fillPoly(mask, [box], color)

def iou_rect(a: Tuple[float,float,float,float], b: Tuple[float,float,float,float]) -> float:
    ax,ay,aw,ah = a; bx,by,bw,bh = b
    x1 = max(ax, bx); y1 = max(ay, by)
    x2 = min(ax+aw, bx+bw); y2 = min(ay+ah, by+bh)
    if x2 <= x1 or y2 <= y1: return 0.0
    inter = (x2-x1)*(y2-y1)
    union = aw*ah + bw*bh - inter
    return inter/union

def sticker_mask(bgr: np.ndarray) -> np.ndarray:
    """V가 밝고 (채도 높거나, 아주 낮은데 밝은 화이트)인 픽셀만 남김"""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    H,S,V = cv2.split(hsv)
    m_color  = (V>90) & (S>50)
    m_white  = (V>180) & (S<40)
    m = (m_color | m_white).astype(np.uint8)*255
    k = cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k, 2)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, 2)
    return m

def is_grid_3x3(centers: np.ndarray, tolerance: float=0.3) -> bool:
    """9개 중심점이 3x3 격자를 형성하는지 검증"""
    if len(centers) != 9:
        return False
    xs = sorted(centers[:,0]); ys = sorted(centers[:,1])
    x_groups = [xs[0:3], xs[3:6], xs[6:9]]
    y_groups = [ys[0:3], ys[3:6], ys[6:9]]
    x_means = [np.mean(g) for g in x_groups]
    y_means = [np.mean(g) for g in y_groups]
    x_spacing = [x_means[1]-x_means[0], x_means[2]-x_means[1]]
    y_spacing = [y_means[1]-y_means[0], y_means[2]-y_means[1]]
    if max(x_spacing) > 0:
        x_ratio = min(x_spacing) / max(x_spacing)
        if x_ratio < (1 - tolerance): return False
    if max(y_spacing) > 0:
        y_ratio = min(y_spacing) / max(y_spacing)
        if y_ratio < (1 - tolerance): return False
    return True

def find_9_stickers(bgr: np.ndarray) -> Tuple[List[tuple], np.ndarray]:
    H,W = bgr.shape[:2]
    mask = sticker_mask(bgr)
    cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 0.001*H*W or area > 0.15*H*W:
            continue
        rr = cv2.minAreaRect(c)
        (cx,cy),(w,h),ang = rr
        if min(w,h) < 18:  # 너무 작으면 제외
            continue
        aspect = min(w,h)/max(w,h)
        rect_area = w*h
        fill_ratio = area/max(1.0,rect_area)
        if aspect < 0.70:     # 거의 정사각형
            continue
        if fill_ratio < 0.55:  # 채움 정도
            continue
        cands.append((rr, area))

    # NMS
    boxes = []
    for rr, area in sorted(cands, key=lambda x:-x[1]):
        (cx,cy),(w,h),ang = rr
        br = (cx-w/2, cy-h/2, w, h)
        if any(iou_rect(br, b) > 0.30 for b,_ in boxes):
            continue
        boxes.append((br, rr))
    rects = [rr for _,rr in boxes]

    if len(rects) < 9:
        return [], mask

    # 9개 이상이면 3x3 격자를 형성하는 조합 찾기
    centers = np.array([rr[0] for rr in rects], np.float32)
    img_center = np.array([W/2, H/2])
    dists = np.sum((centers - img_center)**2, axis=1)
    sorted_idx = np.argsort(dists)
    for i in range(min(len(rects)-8, 20)):
        test_idx = sorted_idx[i:i+9]
        test_centers = centers[test_idx]
        if is_grid_3x3(test_centers, tolerance=0.35):
            rects = [rects[j] for j in test_idx]
            break
    else:
        rects = [rects[j] for j in sorted_idx[:9]]

    return rects[:9], mask

def warp_by_sticker_union(bgr: np.ndarray, rects: List[tuple], size:int=720):
    """9개 스티커 중심점 기반으로 안정적 워핑"""
    H,W = bgr.shape[:2]
    centers = np.array([rr[0] for rr in rects], np.float32)
    hull = cv2.convexHull(centers.astype(np.int32))
    peri = cv2.arcLength(hull, True)
    approx = cv2.approxPolyDP(hull, 0.02*peri, True)
    if len(approx) != 4:
        rect = cv2.minAreaRect(centers)
        quad = cv2.boxPoints(rect).astype(np.float32)
    else:
        quad = approx.reshape(4,2).astype(np.float32)
    center_point = quad.mean(axis=0)
    quad = center_point + (quad - center_point) * 1.2
    quad = order_quad(quad)
    dst = np.array([[0,0],[size-1,0],[size-1,size-1],[0,size-1]], np.float32)
    M = cv2.getPerspectiveTransform(quad, dst)
    warp = cv2.warpPerspective(bgr, M, (size,size))
    mask = np.zeros((H,W), np.uint8)
    cv2.fillPoly(mask, [quad.astype(np.int32)], 255)
    return warp, mask, quad

def tiles_labels_with_numbers(bgr: np.ndarray, margin: float=0.18):
    """HSV 규칙 + YCrCb 보정으로 6색 분류 (ORANGE 우선)"""
    H,W = bgr.shape[:2]
    n=3; ch, cw = H//n, W//n
    hsv   = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)  # 보정용

    S20 = int(np.percentile(hsv[:,:,1], 20))
    V60 = int(np.percentile(hsv[:,:,2], 60))

    def patch(r,c):
        y0,x0=r*ch,c*cw; y1,x1=(r+1)*ch,(c+1)*cw
        yy0,yy1 = int(y0+margin*ch), int(y1-margin*ch)
        xx0,xx1 = int(x0+margin*cw), int(x1-margin*cw)
        return hsv[yy0:yy1, xx0:xx1], ycrcb[yy0:yy1, xx0:xx1]

    def med3(a3):
        if a3.size==0: return np.array([0,0,0],np.float32)
        arr = a3.reshape(-1,3).astype(np.float32)
        v = arr[:,2]; q1,q3 = np.percentile(v,[25,75])
        keep = (v>=q1)&(v<=q3)
        arr = arr[keep] if keep.any() else arr
        return np.median(arr, axis=0)

    def in_range(a,b,x): return (a < x <= b)
    def circ_d(h1,h0):
        d = abs(h1-h0); return min(d, 180-d)

    results=[]; tile_num=1
    for r in range(3):
        for c in range(3):
            hsv_p, ycc_p = patch(r,c)
            Hm,Sm,Vm = med3(hsv_p).astype(int)
            Ym,Crm,Cbm = med3(ycc_p).astype(int)

            # 1) WHITE: 저채도·고명도
            if (Sm < max(30, S20+5)) and (Vm > max(130, V60-10)):
                results.append((tile_num, "WHITE")); tile_num+=1; continue

            label = None

            # 2) ORANGE → RED 우선순위
            # ORANGE: 8~28°, 충분한 S,V
            if in_range(8,28,Hm) and Sm>60 and Vm>85:
                label = "ORANGE"

            # RED: 0~8° 또는 172~180°
            if label is None and ((Hm<=8) or (Hm>=172)) and Sm>60 and Vm>70:
                label = "RED"
                # 경계대(6~22°)에서 Cb 높으면 주황으로 뒤집기
                if (6 < Hm <= 22) and (Cbm >= 115):
                    label = "ORANGE"

            # 3) 나머지 기본색
            if label is None and in_range(28,42,Hm) and Sm>55 and Vm>85:
                label = "YELLOW"
            elif label is None and in_range(42,90,Hm) and Sm>50 and Vm>75:
                label = "GREEN"
            elif label is None and in_range(90,140,Hm) and Sm>45 and Vm>70:
                label = "BLUE"

            # 4) 최근접 중심 보정(안전장치)
            if label is None:
                centers = {
                    "WHITE":  (0,   0, 235),
                    "YELLOW": (31,140,200),
                    "GREEN":  (65,140,180),
                    "BLUE":   (110,140,180),
                    "ORANGE": (20,165,195),
                    "RED":    (0, 180,180),
                }
                def score(c):
                    h0,s0,v0 = centers[c]
                    w = 2.2 if c in ("RED","ORANGE") else 2.0
                    return (w*circ_d(Hm,h0))**2 + (Sm-s0)**2 + (Vm-v0)**2
                label = min(centers.keys(), key=score)

            results.append((tile_num, label))
            tile_num += 1
    return results

def annotate_grid_with_numbers(bgr: np.ndarray, results: List[Tuple[int, str]]) -> np.ndarray:
    vis = bgr.copy()
    H,W = bgr.shape[:2]; n=3; ch,cw = H//n, W//n
    idx = 0
    for r in range(3):
        for c in range(3):
            x0,y0 = c*cw, r*ch; x1,y1=(c+1)*cw,(r+1)*ch
            cv2.rectangle(vis,(x0,y0),(x1,y1),(90,255,90),2)
            tile_num, color = results[idx]
            cv2.putText(vis, str(tile_num), (x0+8, y0+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(vis, str(tile_num), (x0+8, y0+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1, cv2.LINE_AA)
            text_size = cv2.getTextSize(color, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            text_x = x0 + (cw - text_size[0]) // 2
            text_y = y0 + (ch + text_size[1]) // 2
            cv2.putText(vis, color, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(vis, color, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
            idx += 1
    return vis

def process_one(img_path: Path):
    name = img_path.stem
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        print(f"[FAIL] load: {img_path}")
        return

    rects, raw_mask = find_9_stickers(bgr)
    if len(rects) < 9:
        cv2.imwrite(str(OUT_DIR/f"{name}_mask.jpg"), raw_mask)
        print(f"[FAIL] {name}: stickers={len(rects)}, need 9")
        return

    vis = bgr.copy()
    for rr in rects:
        box = cv2.boxPoints(rr).astype(np.int32)
        cv2.polylines(vis, [box], True, (0,255,0), 2)
    cv2.imwrite(str(OUT_DIR/f"{name}_detect.jpg"), vis)

    warp, union_mask, quad = warp_by_sticker_union(bgr, rects, size=720)
    cv2.imwrite(str(OUT_DIR/f"{name}_warp.jpg"), warp)

    results = tiles_labels_with_numbers(warp, margin=0.18)
    grid = annotate_grid_with_numbers(warp, results)
    cv2.imwrite(str(OUT_DIR/f"{name}_grid.jpg"), grid)

    output_data = {
        "file": img_path.as_posix(),
        "tiles": [{"number": num, "color": color} for num, color in results]
    }
    with open(OUT_DIR/f"{name}_colors.json","w",encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] {name}: 9 stickers detected")
    for num, color in results:
        print(f"  타일 {num}: {color}")

def main():
    files = sorted(glob.glob(str(IN_DIR/"*.jpg")))
    if not files:
        print(f"[WARN] {IN_DIR}/*.jpg 없음")
        return
    for fp in files:
        process_one(Path(fp))
    print("\n[DONE] all saved in outputs/")

if __name__ == "__main__":
    main()
