# /// script
# dependencies = ["pillow"]
# ///
"""queue 파일의 "render" 정보로 게시 이미지(1080×1350 JPEG)를 만든다.

사용법 (로컬 · 한글 폰트 필요)
  uv run scripts/render.py                 # render 가 있고 이미지가 없는 queue 전부
  uv run scripts/render.py --force         # 이미 있어도 다시 만든다

render: {"screen": "captures/…png", "headline": "두 줄\\n제목", "sub": "한 줄 설명", "top": 0}
  top = 캡처에서 잘라 쓸 시작 y(px). 잘리는 높이는 레이아웃이 정한다.
폰트: FONT_BOLD / FONT_REGULAR 환경변수, 없으면 Windows 맑은 고딕.
"""

import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1350
BG, LIME, WHITE, DIM, EDGE = "#10120A", "#CBF23B", "#F2F4E9", "#9DA289", "#2A2D22"
SHOT_W, SHOT_TOP, RADIUS = 640, 470, 44
BOLD = os.environ.get("FONT_BOLD", "/mnt/c/Windows/Fonts/malgunbd.ttf")
REGULAR = os.environ.get("FONT_REGULAR", "/mnt/c/Windows/Fonts/malgun.ttf")


def render(spec, out):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    pill = ImageFont.truetype(BOLD, 30)
    d.rounded_rectangle((80, 78, 80 + d.textlength("팀스쿼드", font=pill) + 48, 128), 25, fill=LIME)
    d.text((104, 83), "팀스쿼드", font=pill, fill=BG)

    head = ImageFont.truetype(BOLD, 70)
    d.multiline_text((80, 165), spec["headline"], font=head, fill=WHITE, spacing=18)
    d.text((80, 360), spec["sub"], font=ImageFont.truetype(REGULAR, 36), fill=DIM)

    shot = Image.open(ROOT / spec["screen"]).convert("RGB")
    scale = SHOT_W / shot.width
    src_h = round((H - SHOT_TOP) / scale) + 1
    top = spec.get("top", 0)
    shot = shot.crop((0, top, shot.width, top + src_h)).resize((SHOT_W, H - SHOT_TOP + 1))
    x = (W - SHOT_W) // 2
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SHOT_W, shot.height + RADIUS), RADIUS, fill=255)
    d.rounded_rectangle((x - 8, SHOT_TOP - 8, x + SHOT_W + 8, H + RADIUS), RADIUS + 8, fill=EDGE)
    img.paste(shot, (x, SHOT_TOP), mask)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)


def main():
    force = "--force" in sys.argv
    n = 0
    for f in sorted((ROOT / "queue").glob("*.json")):
        post = json.loads(f.read_text(encoding="utf-8"))
        out = ROOT / post["image"]
        if "render" in post and (force or not out.exists()):
            render(post["render"], out)
            n += 1
    print(f"이미지 {n}개 생성")


if __name__ == "__main__":
    main()
