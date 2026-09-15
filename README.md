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

## 정시 실행은 Supabase pg_cron 이 맡는다

GitHub `schedule` 은 2~6시간씩 늦게 돌아 정시 게시에 못 쓴다(실측 2026-09-14~15). 운영 Supabase 의
`pg_cron` 이 KST 08:05·12:05·19:05 에 `workflow_dispatch` 를 호출하고, GitHub 예약은 예비로 남겨 둔다.
늦게 도착한 실행은 `publish.py` 가 2시간 규칙으로 건너뛴다.

- 크론 작업: `ig-publish-0805` `ig-publish-1205` `ig-publish-1905` (UTC `5 23` `5 3` `5 10`)
- 토큰: Supabase Vault 의 `gh_marketing_dispatch` — 이 레포 `publish.yml` 실행 권한만 있는 fine-grained PAT.
  원본은 `/mnt/d/.secrets/team-squad-marketing/.env` 의 `GH_DISPATCH_TOKEN`.

```sql
-- 상태 확인
select jobname, schedule, active from cron.job where jobname like 'ig-publish-%';
select jobname, status, return_message, start_time from cron.job_run_details
 where jobname like 'ig-publish-%' order by start_time desc limit 5;
select id, status_code, error_msg from net._http_response order by id desc limit 5;  -- 204 면 성공

-- 해제(롤백)
select cron.unschedule('ig-publish-0805'), cron.unschedule('ig-publish-1205'), cron.unschedule('ig-publish-1905');
delete from vault.secrets where name = 'gh_marketing_dispatch';
```

## 수동 실행

```bash
scripts/publish.py --check   # 형식 검사
scripts/publish.py           # 토큰 환경변수가 없으면 드라이런
scripts/publish.py --late    # 2시간 넘게 늦은 글도 발행(24시간 안) — 놓친 글 보충용
```

GitHub 화면에서 실행할 때는 `instagram-publish` 워크플로의 `late` 입력을 켜면 같은 효과다.
