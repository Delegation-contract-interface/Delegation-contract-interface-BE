# Delegation Contract Interface — Backend

위임 계약 기반 AI 에이전트 실행 API입니다. Gemini Function Calling으로 허용된 툴만 노출하고, 범위 초과 시 SSE로 운영자에게 확인을 요청합니다.

## 주요 기능

- **위임 계약 CRUD** — 계약 이름·설명·허용 툴 목록을 Supabase에 저장/조회한다.
- **에이전트 실행** — 계약의 허용 툴만 Gemini에 노출해 Function Calling을 실행한다.
- **경계 확인 요청** — 허용되지 않은 툴 호출 시 `request_confirmation` 툴로 SSE 이벤트를 발행한다.
- **운영자 승인/거절** — `POST /sessions/{id}/confirm`으로 작업 계속 여부를 결정한다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프레임워크 | FastAPI |
| 언어 | Python 3.9 |
| AI | Gemini 2.5 Flash (Function Calling) |
| 데이터베이스 | Supabase (PostgreSQL) |
| 실시간 통신 | SSE (Server-Sent Events) |

## API 엔드포인트

```
GET  /health                          서버 상태 확인
POST /contracts                       위임 계약 생성
GET  /contracts                       위임 계약 목록 조회
GET  /contracts/{id}                  위임 계약 단건 조회
POST /sessions                        에이전트 세션 시작
GET  /sessions/{id}/events            SSE 이벤트 스트림
POST /sessions/{id}/confirm           운영자 승인/거절 (X-Operator-Key 필요)
GET  /sessions/{id}                   세션 상태 조회
```

## 로컬 실행

```bash
# 1. 가상환경 생성 및 의존성 설치
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# GEMINI_API_KEY=...
# SUPABASE_URL=...
# SUPABASE_KEY=...
# OPERATOR_API_KEY=...

# 3. Supabase 테이블 생성 (최초 1회)
# docs/sql/create_tables.sql 참고

# 4. 서버 시작
uvicorn main:app --reload
```

API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

## 관련 레포지토리

- [Delegation-contract-interface-FE](https://github.com/Delegation-contract-interface/Delegation-contract-interface-FE) — Next.js 프론트엔드
