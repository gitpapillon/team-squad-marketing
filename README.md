# team-squad-marketing

팀스쿼드 인스타그램 게시물 예약 발행. 작성 규칙과 주간 절차는 [CLAUDE.md](CLAUDE.md).

## 흐름

주 1회 21개 생성 → PR 검토 → 병합(승인) → `instagram-publish` 워크플로가 매일 KST 08·12·19시에 1건씩 발행 → `state/published.json` 에 기록

## 최초 설정

1. 인스타그램 계정을 **프로페셔널(비즈니스)** 계정으로 전환
2. Meta 개발자 앱 생성 → "Instagram API with Instagram Login" 추가 → 권한 `instagram_business_basic` · `instagram_business_content_publish`
3. 본인 계정을 테스터로 넣고 **장기 토큰(60일)** 발급, 인스타 사용자 ID 확인
4. GitHub 레포 설정
   - Secrets: `IG_USER_ID` · `IG_ACCESS_TOKEN`
   - Variables: `IMAGE_BASE_URL` — `images/` 가 공개로 열리는 주소의 앞부분

토큰 원본은 `/mnt/d/.secrets/team-squad-marketing/` 에 둔다. 레포에 넣지 않는다.

## 토큰 갱신 (60일 만료)

만료 전에 갱신해 `IG_ACCESS_TOKEN` 시크릿을 교체한다.

```bash
curl -s "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=$IG_ACCESS_TOKEN"
```

## 수동 실행

```bash
scripts/publish.py --check   # 형식 검사
scripts/publish.py           # 토큰 환경변수가 없으면 드라이런
```
