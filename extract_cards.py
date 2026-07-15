"""Extrait la carte Pokémon d'un scan de slab gradé (PSA, PCA, ...).

Pour chaque image (.webp, .png, .jpg, ...) du dossier `input` :
  1. détecte le contour de la carte à l'intérieur du slab,
  2. corrige la perspective et recadre au ratio standard 63:88,
  3. sauvegarde en PNG (sans perte, coins arrondis transparents) dans le
     dossier `output`, à la résolution native (aucun agrandissement).

Usage :
    uv run python extract_cards.py [--src DIR] [--out DIR] [--debug]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Ratio officiel d'une carte Pokémon : 63 mm x 88 mm
CARD_RATIO = 63 / 88

# Tolérance sur le ratio des quadrilatères candidats
RATIO_MIN, RATIO_MAX = 0.62, 0.80

# Largeur de travail pour la détection (l'image pleine résolution
# n'est utilisée que pour le recadrage final)
DETECT_WIDTH = 900

# Formats d'image acceptés en entrée
INPUT_EXTENSIONS = {".webp", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordonne 4 points en [haut-gauche, haut-droit, bas-droit, bas-gauche]."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype=np.float32,
    )


def quad_aspect(corners: np.ndarray) -> float:
    """Ratio largeur/hauteur moyen d'un quadrilatère ordonné."""
    tl, tr, br, bl = corners
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    return w / h if h else 0.0


def candidate_quads(
    img: np.ndarray, area_min: float = 0.15, area_max: float = 0.92
) -> list[np.ndarray]:
    """Cherche des quadrilatères "carte" via plusieurs binarisations."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    area_img = img.shape[0] * img.shape[1]
    quads: list[np.ndarray] = []

    masks: list[np.ndarray] = []

    # 1) Contours de Canny (bords nets de la carte dans le slab)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    masks.append(cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2))

    # 2) Saturation : la carte est colorée, le slab plastique est gris/neutre
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    _, sat_mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    sat_mask = cv2.morphologyEx(sat_mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    masks.append(sat_mask)

    # 3) Luminosité (utile si la carte est claire sur fond de slab sombre)
    _, bright = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    masks.append(bright)

    for mask in masks:
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # La carte occupe une part significative du scan, sans être le slab entier
            if not (area_min * area_img < area < area_max * area_img):
                continue
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
            if len(approx) != 4:
                rect = cv2.minAreaRect(hull)
                approx = cv2.boxPoints(rect).reshape(-1, 1, 2)
                # le rectangle englobant ne doit pas trop dépasser le contour réel
                if cv2.contourArea(approx.astype(np.int32)) > area * 1.25:
                    continue
            corners = order_corners(approx)
            if RATIO_MIN <= quad_aspect(corners) <= RATIO_MAX:
                quads.append(corners)

    return quads


def pick_best_quad(quads: list[np.ndarray]) -> np.ndarray | None:
    """Choisit le plus grand quadrilatère au ratio le plus proche de 63:88."""
    if not quads:
        return None

    def score(q: np.ndarray) -> float:
        area = cv2.contourArea(q.astype(np.int32))
        ratio_penalty = abs(quad_aspect(q) - CARD_RATIO) / CARD_RATIO
        return area * (1 - ratio_penalty)

    return max(quads, key=score)


def refine_corners(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Resserre le cadrage si la carte n'occupe pas tout le quadrilatère détecté.

    Warpe une prévisualisation du cadrage courant, y re-cherche un
    quadrilatère "carte" nettement plus petit que le cadre, et si trouvé,
    reprojette ses coins dans le repère de l'image d'origine.
    """
    prev_w = DETECT_WIDTH
    prev_h = int(round(prev_w / CARD_RATIO))
    dst = np.array(
        [[0, 0], [prev_w - 1, 0], [prev_w - 1, prev_h - 1], [0, prev_h - 1]],
        dtype=np.float32,
    )
    for _ in range(3):
        matrix = cv2.getPerspectiveTransform(corners, dst)
        preview = cv2.warpPerspective(img, matrix, (prev_w, prev_h), flags=cv2.INTER_AREA)

        inner = pick_best_quad(candidate_quads(preview, area_min=0.55, area_max=0.96))
        if inner is None:
            break

        back = cv2.perspectiveTransform(inner.reshape(-1, 1, 2), np.linalg.inv(matrix))
        corners = back.reshape(4, 2).astype(np.float32)
    return corners


# Facteur d'élargissement de l'aperçu pendant le calage fin des bords
EXPAND = 1.06


def _first_saturated(profile: np.ndarray, jump: float = 35.0, run: int = 4) -> int | None:
    """Index de la première montée durable de chroma, en scannant
    depuis l'extérieur (index 0 = bord extérieur du profil)."""
    base = float(np.median(profile[:6]))
    above = profile > base + jump
    for i in range(len(above) - run):
        if above[i : i + run].all():
            return i
    return None


def snap_edges(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Cale précisément chaque bord de la carte sur la frontière carte/slab.

    Le quadrilatère détecté peut rester décalé ou légèrement tourné : il
    reste alors une bande ou un biseau de slab dans le recadrage. On
    redresse un aperçu légèrement élargi, puis chaque bord est modélisé
    comme une DROITE. La frontière est trouvée par CHROMA (max(R,V,B) -
    min(R,V,B)) : quasi nulle sur le plastique noir, gris ou blanc de la
    coque, élevée sur le bord imprimé de la carte. (La saturation HSV ne
    convient pas : elle est instable sur les pixels sombres.)

    Chaque bord est mesuré en 6 points, puis la droite ajustée est
    décalée vers l'intérieur jusqu'à passer À L'INTÉRIEUR de toutes les
    mesures (enveloppe) : une carte légèrement bombée dans sa coque ne
    laisse ainsi aucun biseau de slab, au prix d'une frange de bordure
    d'au plus quelques pixels. Les coins corrigés sont les intersections
    des 4 droites, reprojetées dans l'image d'origine. Deux passes pour
    converger.
    """
    prev_w = DETECT_WIDTH
    prev_h = int(round(prev_w / CARD_RATIO))
    dst = np.array(
        [[0, 0], [prev_w - 1, 0], [prev_w - 1, prev_h - 1], [0, prev_h - 1]],
        dtype=np.float32,
    )
    inset = 2  # retrait (px aperçu) pour ne pas garder le halo de transition
    # Marge attendue autour de la carte dans l'aperçu élargi : sert de
    # position de repli quand aucun croisement net n'est trouvé
    margin = (1 - 1 / EXPAND) / 2
    segments = 6  # mesures par bord

    for _ in range(2):
        center = corners.mean(axis=0)
        expanded = (center + (corners - center) * EXPAND).astype(np.float32)

        matrix = cv2.getPerspectiveTransform(expanded, dst)
        preview = cv2.warpPerspective(img, matrix, (prev_w, prev_h), flags=cv2.INTER_AREA)

        chan = preview.astype(np.float32)
        chroma = cv2.GaussianBlur(chan.max(axis=2) - chan.min(axis=2), (5, 5), 0)

        bx, by = int(0.10 * prev_w), int(0.10 * prev_h)  # zones de recherche

        def edge_line(side: str) -> tuple[float, float]:
            """Droite d'un bord : x = a + b*y ('L'/'R') ou y = a + b*x ('T'/'B').

            Mesure la distance bord extérieur -> carte en `segments` points
            de la portion centrale (coins arrondis exclus), ajuste une
            droite, puis la décale vers l'intérieur pour englober toutes
            les mesures (au cas où la carte est légèrement bombée).
            """
            length = prev_h if side in "LR" else prev_w
            coords, dists = [], []
            t0, t1 = 0.15, 0.85
            for k in range(segments):
                s0 = int((t0 + (t1 - t0) * k / segments) * length)
                s1 = int((t0 + (t1 - t0) * (k + 1) / segments) * length)
                span = slice(s0, s1)
                if side == "L":
                    prof = chroma[span, :bx].mean(axis=0)
                elif side == "R":
                    prof = chroma[span, prev_w - bx :].mean(axis=0)[::-1]
                elif side == "T":
                    prof = chroma[:by, span].mean(axis=1)
                else:
                    prof = chroma[prev_h - by :, span].mean(axis=1)[::-1]
                idx = _first_saturated(prof)
                if idx is not None:
                    coords.append((s0 + s1) / 2)
                    dists.append(float(idx))

            if len(dists) < 2:
                a, b = margin * (prev_w if side in "LR" else prev_h), 0.0
            else:
                c = np.array(coords)
                d = np.array(dists)
                b, a = np.polyfit(c, d, 1)
                # Enveloppe : décale la droite vers l'intérieur jusqu'à
                # couvrir toutes les mesures ; le pire écart est ignoré
                # s'il est isolé (poussière, reflet ponctuel).
                resid = np.sort(d - (a + b * c))
                shift = resid[-1]
                if len(resid) >= 3 and resid[-1] - resid[-2] > 4:
                    shift = resid[-2]
                a += max(0.0, float(shift))
            a += inset

            # Conversion en coordonnées absolues de l'aperçu
            if side == "L":
                return a, b
            if side == "R":
                return prev_w - 1 - a, -b
            if side == "T":
                return a, b
            return prev_h - 1 - a, -b

        aL, bL = edge_line("L")
        aR, bR = edge_line("R")
        aT, bT = edge_line("T")
        aB, bB = edge_line("B")

        def intersect(av: float, bv: float, ah: float, bh: float) -> list[float]:
            # x = av + bv*y ; y = ah + bh*x
            x = (av + bv * ah) / (1 - bv * bh)
            return [x, ah + bh * x]

        snapped = np.array(
            [
                intersect(aL, bL, aT, bT),
                intersect(aR, bR, aT, bT),
                intersect(aR, bR, aB, bB),
                intersect(aL, bL, aB, bB),
            ],
            dtype=np.float32,
        )
        back = cv2.perspectiveTransform(snapped.reshape(-1, 1, 2), np.linalg.inv(matrix))
        corners = back.reshape(4, 2).astype(np.float32)
    return corners

def extract_card(path: Path, out_dir: Path, debug_dir: Path | None) -> bool:
    data = np.fromfile(path, dtype=np.uint8)  # gère les chemins Windows/accents
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"  [ERREUR] Lecture impossible : {path.name}")
        return False

    h, w = img.shape[:2]
    scale = DETECT_WIDTH / w
    small = cv2.resize(img, (DETECT_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)

    best = pick_best_quad(candidate_quads(small))
    if best is None:
        print(f"  [ECHEC] Carte non détectée : {path.name}")
        return False

    corners = best / scale  # retour aux coordonnées pleine résolution

    # Passe de raffinement : si le premier cadrage contient encore une marge
    # de slab autour de la carte, on re-détecte dans ce cadrage et on ramène
    # les coins dans le repère de l'image d'origine (un seul warp final).
    corners = refine_corners(img, corners)
    # Ajustement fin : chaque bord est calé sur la frontière carte/fond.
    corners = snap_edges(img, corners)

    if debug_dir is not None:
        dbg = img.copy()
        cv2.polylines(dbg, [corners.astype(np.int32)], True, (0, 0, 255), max(3, w // 400))
        ok, buf = cv2.imencode(".jpg", dbg, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            (debug_dir / f"{path.stem}_debug.jpg").write_bytes(buf.tobytes())

    # Dimensions de sortie : résolution native détectée, forcée au ratio 63:88
    tl, tr, br, bl = corners
    width_px = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    height_px = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    # on garde la plus grande dimension mesurée et on dérive l'autre du ratio
    out_h = int(round(max(height_px, width_px / CARD_RATIO)))
    out_w = int(round(out_h * CARD_RATIO))

    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, dst)
    card = cv2.warpPerspective(img, matrix, (out_w, out_h), flags=cv2.INTER_CUBIC)

    # Coins transparents suivant l'arrondi officiel (~3 mm de rayon) :
    # les coins de la carte étant arrondis, les angles de l'image
    # laisseraient sinon apparaître des triangles de coque.
    radius = int(round(out_w * 3 / 63))
    mask = np.zeros((out_h, out_w), dtype=np.uint8)
    cv2.rectangle(mask, (radius, 0), (out_w - 1 - radius, out_h - 1), 255, -1)
    cv2.rectangle(mask, (0, radius), (out_w - 1, out_h - 1 - radius), 255, -1)
    for cx in (radius, out_w - 1 - radius):
        for cy in (radius, out_h - 1 - radius):
            cv2.circle(mask, (cx, cy), radius, 255, -1)
    card = cv2.cvtColor(card, cv2.COLOR_BGR2BGRA)
    card[:, :, 3] = mask

    out_path = out_dir / f"{path.stem}_carte.png"
    ok, buf = cv2.imencode(".png", card, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:
        print(f"  [ERREUR] Encodage PNG : {path.name}")
        return False
    out_path.write_bytes(buf.tobytes())
    print(f"  [OK] {path.name} -> {out_path.name} ({out_w}x{out_h})")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=Path("input"), help="dossier des scans")
    parser.add_argument("--out", type=Path, default=Path("output"), help="dossier de sortie")
    parser.add_argument("--debug", action="store_true", help="sauver les contours détectés dans out/debug")
    args = parser.parse_args()

    if not args.src.is_dir():
        args.src.mkdir(parents=True, exist_ok=True)
        print(f"Le dossier {args.src} n'existait pas : il vient d'être créé.")
        print("Placez-y vos scans de cartes puis relancez le programme.")
        return 1

    files = sorted(
        f
        for f in args.src.iterdir()
        if f.suffix.lower() in INPUT_EXTENSIONS and not f.stem.endswith("_carte")
    )
    if not files:
        print(f"Aucune image trouvée dans {args.src.resolve()}")
        print(f"Formats acceptés : {', '.join(sorted(INPUT_EXTENSIONS))}")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    debug_dir = None
    if args.debug:
        debug_dir = args.out / "debug"
        debug_dir.mkdir(exist_ok=True)

    print(f"{len(files)} image(s) à traiter -> {args.out.resolve()}")
    failures = sum(not extract_card(f, args.out, debug_dir) for f in files)
    if failures:
        print(f"\n{failures} échec(s) sur {len(files)}.")
        return 2
    print("\nTerminé sans erreur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
