#!/usr/bin/env python3
"""인스타그램 예약 발행기 — main 에 병합된 queue 게시물 중 시각이 된 것을 발행한다.

사용법
  scripts/publish.py            # 시각이 된 게시물 1건 발행 (토큰 없으면 드라이런)
  scripts/publish.py --check    # queue 전체 형식 검사만 (PR 검사용)

queue 파일: queue/<YYYY-MM-DD>-<슬롯>.json  →  {"image": "images/…jpg", "caption": "…"}
슬롯 시각(KST): 1=08시 · 2=12시 · 3=19시. 2시간 넘게 지난 게시물은 발행하지 않고 건너뛴다
(예약 실행이 늦어 새벽에 올라가는 것을 막는다 — 수동 실행은 --late 로 허용).

환경변수: IG_USER_ID · IG_ACCESS_TOKEN · IMAGE_BASE_URL (이미지 공개 주소의 앞부분)
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
API = "https://graph.instagram.com/v25.0"
SLOT_HOURS = {1: 8, 2: 12, 3: 19}
LATE_LIMIT = timedelta(hours=2)
STATE = ROOT / "state" / "published.json"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-([123])$")


def load_queue():
    posts = []
    for f in sorted((ROOT / "queue").glob("*.json")):
        m = NAME.match(f.stem)
        if not m:
            raise SystemExit(f"❌ 파일 이름 형식 오류: {f.name}")
        at = datetime.fromisoformat(m[1]).replace(hour=SLOT_HOURS[int(m[2])], tzinfo=KST)
        posts.append((f.stem, at, json.loads(f.read_text(encoding="utf-8"))))
    return posts


def problems(post):
    """게시 전 규칙 위반 목록. 규칙 원문은 CLAUDE.md."""
    out = []
    img = ROOT / post.get("image", "")
    cap = post.get("caption", "")
    if not post.get("image", "").lower().endswith((".jpg", ".jpeg")):
        out.append("이미지는 JPEG 만 가능")
    elif not img.is_file():
        out.append(f"이미지 없음: {post.get('image')}")
    if not cap.startswith("[앱 홍보]"):
        out.append("첫 줄이 [앱 홍보] 로 시작하지 않음")
    if "#앱홍보" not in cap:
        out.append("#앱홍보 해시태그 없음")
    if len(cap) > 2200:
        out.append(f"캡션 {len(cap)}자 > 2200")
    if len(re.findall(r"#\S+", cap)) > 30:
        out.append("해시태그 30개 초과")
    return out


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        url, data = f"{url}?{data.decode()}", None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method), timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"❌ {method} {path} → {e.code}: {e.read().decode(errors='replace')}")


def publish(post):
    uid = os.environ["IG_USER_ID"]
    image_url = os.environ["IMAGE_BASE_URL"].rstrip("/") + "/" + post["image"]
    container = call("POST", f"{uid}/media", image_url=image_url, caption=post["caption"])["id"]
    for _ in range(30):
        status = call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise SystemExit(f"❌ 컨테이너 상태 {status}")
        time.sleep(5)
    else:
        raise SystemExit("❌ 컨테이너 처리 대기 시간 초과")
    return call("POST", f"{uid}/media_publish", creation_id=container)["id"]


def main():
    posts = load_queue()
    bad = [(k, p) for k, _, post in posts for p in problems(post)]
    for k, p in bad:
        print(f"❌ {k}: {p}")
    if "--check" in sys.argv:
        print(f"검사 {len(posts)}건 · 위반 {len(bad)}건")
        return 1 if bad else 0

    now = datetime.now(KST)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    due = [(k, at, post) for k, at, post in posts
           if k not in state and at <= now and not any(b[0] == k for b in bad)]
    limit = timedelta(hours=24) if "--late" in sys.argv else LATE_LIMIT
    for k, at, _ in due:
        if at < now - limit:
            print(f"⏭ {k}: 예정보다 {limit} 넘게 지나 건너뜀")
    due = [d for d in due if d[1] >= now - limit]
    if not due:
        print("발행할 게시물 없음")
        return 0

    key, _, post = due[0]  # 한 번 실행에 1건만
    if not os.environ.get("IG_ACCESS_TOKEN"):
        print(f"[드라이런] {key}\n{post['caption']}")
        return 0
    media_id = publish(post)
    state[key] = {"media_id": media_id, "at": now.isoformat(timespec="seconds")}
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ {key} 발행 → {media_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
