# Codex 개발 인수인계

저장소: pine91/ai-quant-platform-v2, main. V1 저장소는 변경하지 말 것.
목표: AI 서비스 개발자 포트폴리오. Windows 로컬 실행 지원.

## 현재 상태
FastAPI, React/TypeScript/Vite, Lightweight Charts. 검은 차트, 상승 빨강/하락 파랑. 기본 5분봉. Bithumb 가상자산, Yahoo Finance 국내 KOSPI/KOSDAQ 및 미국 주식. 미국 정규장/프리/애프터 선택 구현. 정규장 4시간봉 집계 코드 있음. Alpaca BOATS 오버나이트 어댑터는 ENABLE_OVERNIGHT=false 기본값 유지. 실제 API 권한/키 없음. KRX/NXT 분리 미구현. 전체 빌드 및 실행 테스트 미실행.

## 우선순위
1. 현재 소스 검토 및 pytest, npm build 실행. Windows zoneinfo용 tzdata 의존성 확인. 모의 HTTP 응답으로 API 테스트, 4시간봉 OHLC 및 DST/거래일 경계 검증. 실제 API 오류와 빈 데이터 처리. React 세션 선택 및 차트 갱신 검증.
2. KRX/NXT 분리: 한국투자증권 공식 API 문서 확인 후 어댑터 구현. 키가 없으면 명시적 미설정 상태, Yahoo 데이터에 NXT 라벨을 붙이지 말 것.
3. EMA20/60, RSI14, 피보나치 지표와 차트 표시, 테스트.
4. AI Agent: 읽기 전용 도구 호출, 근거 및 데이터 시각 표시, OpenAI 키 환경변수 관리.
5. 백테스팅 및 모의투자: 수수료/슬리피지, 미래 데이터 참조 방지. 실제 주문 금지.
6. PostgreSQL, Redis, 마이그레이션 및 캐시.
7. Docker Compose, GitHub Actions CI, Windows 설치 README, .env.example (실제 키 금지).

기능별 작은 커밋과 테스트. 가능한 작업은 계속 진행하되 외부 자격증명/권한이 필요한 부분은 차단 상태로 기록하고 다른 작업을 진행. 실행하지 않은 테스트를 성공으로 보고하지 말 것. 공개 저장소에 비밀정보 금지. 완료 시 변경사항, 테스트 결과, 남은 제약 보고.
