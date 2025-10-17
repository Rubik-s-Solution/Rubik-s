# cube_face_reader.py
# 9개 스티커 검출 + 3x3 격자만 선택 + 실패시 '엄격 후보 헐(Convex Hull)' 기반 외곽-워핑
# 추가: 워프 후 타일별 '엄격 마스크'로 실제 스티커 내부를 재탐색하여 색상 샘플링(마스크-가이드)

import cv2, numpy as np, json, glob
from pathlib import Path
from typing import List, Tuple

IN_DIR  = Path("uploaded_images")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- utils ----------
def order_quad(pts: np.ndarray) -> np.ndarray:
    pts = np.array(pts, dtype=np.float32).reshape(-1,2)
    s = pts.sum(1); d = np.diff(pts, axis=1).reshape(-1)
    out = np.zeros((4,2), np.float32)
    out[0] = pts[np.argmin(s)]  # TL
    out[2] = pts[np.argmax(s)]  # BR
    out[1] = pts[np.argmin(d)]  # TR
    out[3] = pts[np.argmax(d)]  # BL
    return out

def iou_rect(a, b) -> float:
    ax,ay,aw,ah = a; bx,by,bw,bh = b
    x1 = max(ax, bx); y1 = max(ay, by)
    x2 = min(ax+aw, bx+bw); y2 = min(ay+ah, by+bh)
    if x2 <= x1 or y2 <= y1: return 0.0
    inter = (x2-x1)*(y2-y1)
    union = aw*ah + bw*bh - inter
    return inter/union

# ---------- masks ----------
def _clahe_bgr(bgr):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    l = cv2.createCLAHE(2.0, (8,8)).apply(l)
    return cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)

def sticker_mask(bgr: np.ndarray) -> np.ndarray:
    """일반 모드: CLAHE + HSV 임계 + Otsu 보조(AND) + OPEN/CLOSE"""
    bgr = _clahe_bgr(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    H,S,V = cv2.split(hsv)

    v_mean, v_std = float(np.mean(V)), float(np.std(V))
    s_mean        = float(np.mean(S))

    v_t = max(65, min(105, v_mean - 0.5*v_std))
    s_t = max(30, min(55,  s_mean - 0.3*v_std))
    m_color = (V > v_t) & (S > s_t)

    white_v  = max(150, v_mean + 0.2*v_std) if v_mean > 95 else 145
    m_white  = (V > white_v) & (S < 55)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(cv2.GaussianBlur(gray,(5,5),0), 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    m = ((m_color | m_white) & (V > 90)).astype(np.uint8)*255
    m = cv2.bitwise_or(m, (otsu & (S>35)).astype(np.uint8))

    k1 = cv2.getStructuringElement(cv2.MORPH_RECT,(3,3))
    k2 = cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
    m  = cv2.morphologyEx(m, cv2.MORPH_OPEN,  k1, 1)
    m  = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k2, 2)
    return m

def sticker_mask_strict(bgr: np.ndarray) -> np.ndarray:
    """엄격 모드: Otsu 제외, S/V 하한 강화 → 스티커만 남김 (fallback/샘플링 가이드용)"""
    bgr = _clahe_bgr(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    H,S,V = cv2.split(hsv)

    v_mean, v_std = float(np.mean(V)), float(np.std(V))
    s_mean        = float(np.mean(S))

    v_t = max(80, min(115, v_mean - 0.3*v_std))
    s_t = max(45, min(70,  s_mean - 0.2*v_std))
    m_color = (V > v_t) & (S > s_t)

    white_v  = max(165, v_mean + 0.4*v_std) if v_mean > 95 else 160
    m_white  = (V > white_v) & (S < 45)

    m = (m_color | m_white).astype(np.uint8)*255
    k1 = cv2.getStructuringElement(cv2.MORPH_RECT,(3,3))
    k2 = cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
    m  = cv2.morphologyEx(m, cv2.MORPH_OPEN,  k1, 1)
    m  = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k2, 2)
    return m

# ---------- grid check ----------
def is_grid_3x3(centers: np.ndarray, tol: float=0.3) -> bool:
    if len(centers) != 9: return False
    xs = sorted(centers[:,0]); ys = sorted(centers[:,1])
    xg = [xs[0:3], xs[3:6], xs[6:9]]
    yg = [ys[0:3], ys[3:6], ys[6:9]]
    xm = [np.mean(g) for g in xg]
    ym = [np.mean(g) for g in yg]
    xs_gap = [xm[1]-xm[0], xm[2]-xm[1]]
    ys_gap = [ym[1]-ym[0], ym[2]-ym[1]]
    if max(xs_gap)>0 and min(xs_gap)/max(xs_gap) < (1-tol): return False
    if max(ys_gap)>0 and min(ys_gap)/max(ys_gap) < (1-tol): return False
    return True

# ---------- detection ----------
def _collect_square_candidates(mask, min_area, max_area):
    cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands=[]
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area: continue
        rr = cv2.minAreaRect(c)
        (cx,cy),(w,h),ang = rr
        if min(w,h) < 12: continue
        aspect = min(w,h)/max(w,h) if max(w,h)>0 else 0
        rect_area = max(1.0, w*h)
        fill_ratio = area/rect_area
        if aspect < 0.58: continue
        if fill_ratio < 0.38: continue
        cands.append((rr, area))
    # NMS with higher IoU
    boxes=[]
    for rr,_ in sorted(cands, key=lambda x:-x[1]):
        (cx,cy),(w,h),_ = rr
        br=(cx-w/2, cy-h/2, w, h)
        if any(iou_rect(br,b)>0.45 for b,_ in boxes): continue
        boxes.append((br,rr))
    rects=[rr for _,rr in boxes]
    return rects

def find_9_stickers(bgr: np.ndarray):
    H,W=bgr.shape[:2]
    mask = sticker_mask(bgr)
    rects = _collect_square_candidates(mask, min_area=max(0.0005*H*W,250), max_area=0.22*H*W)

    if len(rects) >= 9:
        centers = np.array([rr[0] for rr in rects], np.float32)
        imgc = np.array([W/2, H/2])
        d = np.sum((centers-imgc)**2, axis=1)
        sidx = np.argsort(d)
        for i in range(min(len(rects)-8, 20)):
            test = sidx[i:i+9]
            if is_grid_3x3(centers[test], tol=0.35):
                rects = [rects[j] for j in test]; break
        else:
            rects = [rects[j] for j in sidx[:9]]
        return rects, mask

    # 8개면: 가짜 9번째 삽입
    if len(rects) == 8:
        centers = np.array([rr[0] for rr in rects], np.float32)
        xs = sorted(centers[:,0]); ys = sorted(centers[:,1])
        if len(xs) >= 9 and len(ys) >= 9:
            xm = [np.mean(xs[i*3:(i+1)*3]) for i in range(3)]
            ym = [np.mean(ys[i*3:(i+1)*3]) for i in range(3)]
            dx = (xm[2]-xm[0])/2; dy=(ym[2]-ym[0])/2
            ws=[rr[1][0] for rr in rects]; hs=[rr[1][1] for rr in rects]
            w=float(np.median(ws)); h=float(np.median(hs))
            grid=[(xm[i],ym[j]) for j in range(3) for i in range(3)]
            def near(p, pts, th): return any(np.hypot(p[0]-q[0],p[1]-q[1])<th for q in pts)
            th=0.6*min(dx,dy)
            miss=None
            for p in grid:
                if not near(p, centers, th):
                    miss=p; break
            if miss is not None:
                fake=((miss[0],miss[1]), (w,h), 0.0)
                rects.append(fake)
                return rects, mask

    return rects, mask  # <9일 수도 있음 → fallback에서 처리

# ---------- warp ----------
def warp_by_candidates_hull(bgr: np.ndarray, rects: List[tuple], size:int=720):
    """후보 중심점들의 컨벡스헐을 4점 근사(없으면 minAreaRect) → 워핑"""
    H,W=bgr.shape[:2]
    centers = np.array([rr[0] for rr in rects], np.float32)
    if len(centers) >= 3:
        hull = cv2.convexHull(centers.astype(np.int32))
        peri = cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, 0.02*peri, True)
        if len(approx)==4:
            quad=approx.reshape(4,2).astype(np.float32)
        else:
            quad=cv2.boxPoints(cv2.minAreaRect(centers)).astype(np.float32)
    else:
        cx,cy=W/2,H/2; s=min(W,H)*0.6
        quad=np.array([[cx-s/2,cy-s/2],[cx+s/2,cy-s/2],[cx+s/2,cy+s/2],[cx-s/2,cy+s/2]],np.float32)

    center=quad.mean(axis=0); quad = center + (quad-center)*1.15
    quad = order_quad(quad)
    dst  = np.array([[0,0],[size-1,0],[size-1,size-1],[0,size-1]], np.float32)
    M = cv2.getPerspectiveTransform(quad, dst)
    warp = cv2.warpPerspective(bgr, M, (size,size))
    return warp, quad

# ---------- color classify (mask-guided) ----------
def tiles_labels_mask_guided(warp_bgr: np.ndarray,
                             base_margin: float = 0.12,
                             min_fill: float = 0.12):
    """
    워프된 이미지에서 타일별로 '엄격 마스크'를 이용해 실제 스티커 안쪽 영역을 찾아 샘플링.
    - base_margin: 그리드 ROI 기본 마진(워프 오차 대비)
    - min_fill   : ROI 대비 마스크 점유율이 이보다 작으면 고정마진으로 폴백
    """
    H,W = warp_bgr.shape[:2]; ch, cw = H//3, W//3

    # 프레임/그림자 제거를 포함한 스티커 마스크
    m_strict = sticker_mask_strict(warp_bgr)
    gray = cv2.cvtColor(warp_bgr, cv2.COLOR_BGR2GRAY)
    m_frame = (gray < 70).astype(np.uint8) * 255
    m_sticker = cv2.bitwise_and(m_strict, cv2.bitwise_not(m_frame))
    m_sticker = cv2.morphologyEx(m_sticker, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)), 1)

    hsv   = cv2.cvtColor(warp_bgr, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(warp_bgr, cv2.COLOR_BGR2YCrCb)
    S20 = int(np.percentile(hsv[:,:,1], 20))
    V60 = int(np.percentile(hsv[:,:,2], 60))

    def robust_med(a3):
        if a3.size==0: return (0,0,0), (0,0,0)
        arr = a3.reshape(-1,3).astype(np.float32)
        v = arr[:,2]; q1,q3 = np.percentile(v,[25,75]); keep=(v>=q1)&(v<=q3)
        if keep.any(): arr = arr[keep]
        return tuple(np.median(arr,axis=0)), tuple(np.var(arr,axis=0))

    def circ_d(h1,h0):
        d = abs(h1-h0); return min(d, 180-d)

    results=[]
    for r in range(3):
        for c in range(3):
            y0,x0 = r*ch, c*cw; y1,x1 = (r+1)*ch, (c+1)*cw
            yy0,yy1 = int(y0+base_margin*ch), int(y1-base_margin*ch)
            xx0,xx1 = int(x0+base_margin*cw), int(x1-base_margin*cw)

            roi_mask = m_sticker[yy0:yy1, xx0:xx1]
            h_roi, w_roi = roi_mask.shape[:2]
            chosen = None

            if roi_mask.size>0 and np.count_nonzero(roi_mask) > min_fill*h_roi*w_roi:
                cnts,_ = cv2.findContours(roi_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
                if cnts:
                    (cx,cy),(w,h),ang = cv2.minAreaRect(cnts[0])
                    side = int(0.8*min(float(w), float(h)))
                    cx,cy = int(cx), int(cy)
                    xs = max(0, cx - side//2); xe = min(w_roi, cx + side//2)
                    ys = max(0, cy - side//2); ye = min(h_roi, cy + side//2)
                    if xe-xs>6 and ye-ys>6:
                        chosen = (yy0+ys, yy0+ye, xx0+xs, xx0+xe)

            if chosen is None:
                chosen = (yy0, yy1, xx0, xx1)

            ya,yb,xa,xb = chosen
            hsv_p  = hsv[ya:yb, xa:xb]
            ycc_p  = ycrcb[ya:yb, xa:xb]
            (Hm,Sm,Vm), var = robust_med(hsv_p)
            (_,_,Cbv), _   = robust_med(ycc_p)
            Hm,Sm,Vm = int(Hm),int(Sm),int(Vm)

            # 배경/프레임 차단
            if (Sm < max(25, S20)) and (Vm < max(140, V60+10)):
                label = "UNKNOWN"
            elif np.mean(var) < 25 and Sm < 28:
                label = "UNKNOWN"
            else:
                label=None
                # WHITE
                if (Sm < max(30, S20+5)) and (Vm > max(130, V60-10)):
                    label="WHITE"
                # ORANGE 우선
                if label is None and (8 < Hm <= 28) and Sm>60 and Vm>85:
                    label="ORANGE"
                # RED
                if label is None and ((Hm<=8) or (Hm>=172)) and Sm>60 and Vm>70:
                    label="RED"
                    if (6 < Hm <= 22) and (Cbv >= 115): label="ORANGE"
                # 나머지
                if label is None and (28 < Hm <= 42) and Sm>55 and Vm>85:
                    label="YELLOW"
                elif label is None and (42 < Hm <= 90) and Sm>50 and Vm>75:
                    label="GREEN"
                elif label is None and (90 < Hm <= 140) and Sm>45 and Vm>70:
                    label="BLUE"

                if label is None:
                    centers={"WHITE":(0,0,235),"YELLOW":(31,140,200),"GREEN":(65,140,180),
                             "BLUE":(110,140,180),"ORANGE":(20,165,195),"RED":(0,180,180)}
                    def score(c):
                        h0,s0,v0=centers[c]; w=2.2 if c in ("RED","ORANGE") else 2.0
                        return (w*circ_d(Hm,h0))**2 + (Sm-s0)**2 + (Vm-v0)**2
                    label=min(centers.keys(), key=score)

            results.append((r*3+c+1, label))
    return results

# ---------- visualize ----------
def annotate_grid_with_numbers(bgr: np.ndarray, results: List[Tuple[int,str]], fake_idx: int=-1) -> np.ndarray:
    vis=bgr.copy(); H,W=bgr.shape[:2]; ch,cw=H//3,W//3; i=0
    for r in range(3):
        for c in range(3):
            x0,y0=c*cw, r*ch; x1,y1=(c+1)*cw,(r+1)*ch
            if i==fake_idx:
                cv2.rectangle(vis,(x0,y0),(x1,y1),(0,0,255),2, lineType=cv2.LINE_4)  # 가짜 9번째
            else:
                cv2.rectangle(vis,(x0,y0),(x1,y1),(90,255,90),2)
            tnum,color=results[i]; i+=1
            cv2.putText(vis, str(tnum), (x0+8, y0+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(vis, str(tnum), (x0+8, y0+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1, cv2.LINE_AA)
            ts = cv2.getTextSize(color, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            tx = x0 + (cw - ts[0]) // 2; ty = y0 + (ch + ts[1]) // 2
            cv2.putText(vis, color, (tx,ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(vis, color, (tx,ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
    return vis

# ---------- pipeline ----------
def process_one(img_path: Path, save_debug=True):
    name=img_path.stem
    bgr=cv2.imread(str(img_path))
    if bgr is None:
        print(f"[FAIL] load: {img_path}"); return

    # 해상도 정규화
    MAX_W=1280; H0,W0=bgr.shape[:2]
    if W0 > MAX_W:
        s=MAX_W/W0; bgr=cv2.resize(bgr,(int(W0*s),int(H0*s)), cv2.INTER_AREA)

    # 1) 일반 검출
    rects, m_norm = find_9_stickers(bgr)
    if save_debug: cv2.imwrite(str(OUT_DIR/f"{name}_mask.jpg"), m_norm)

    if len(rects) >= 9:
        vis=bgr.copy()
        for rr in rects:
            box=cv2.boxPoints(rr).astype(np.int32)
            cv2.polylines(vis,[box],True,(0,255,0),2)
        cv2.imwrite(str(OUT_DIR/f"{name}_detect.jpg"), vis)
        warp, quad = warp_by_candidates_hull(bgr, rects, size=720)
        fallback_used = False
    else:
        # 2) Fallback: 엄격 마스크 -> 후보 모아 헐 기반 워핑
        m_strict = sticker_mask_strict(bgr)
        if save_debug: cv2.imwrite(str(OUT_DIR/f"{name}_mask_strict.jpg"), m_strict)
        rects_fb = _collect_square_candidates(m_strict, min_area=max(0.0005*bgr.shape[0]*bgr.shape[1], 200),
                                              max_area=0.25*bgr.shape[0]*bgr.shape[1])
        warp, quad = warp_by_candidates_hull(bgr, rects_fb, size=720)
        fallback_used = True

    # 3) 워프 후 색 분류(마스크-가이드)
    results = tiles_labels_mask_guided(warp, base_margin=0.12, min_fill=0.12)
    grid = annotate_grid_with_numbers(warp, results, fake_idx=-1)
    suffix = "grid" if not fallback_used else "grid_fallback"
    cv2.imwrite(str(OUT_DIR/f"{name}_{suffix}.jpg"), grid)
    cv2.imwrite(str(OUT_DIR/f"{name}_warp.jpg"), warp)

    out = {"file": img_path.as_posix(),
           "tiles": [{"number": n, "color": c} for n,c in results],
           "fallback": fallback_used}
    with open(OUT_DIR/f"{name}_colors.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    tag = "OK" if not fallback_used else "OK-FALLBACK"
    print(f"[{tag}] {name}: {('9 stickers' if not fallback_used else 'fallback hull warp')}")

def main():
    files = sorted(glob.glob(str(IN_DIR/"*.jpg")))
    if not files:
        print(f"[WARN] {IN_DIR}/*.jpg 없음"); return
    for fp in files: process_one(Path(fp))
    print("\n[DONE] all saved in outputs/")

if __name__ == "__main__":
    main()
