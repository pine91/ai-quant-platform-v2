# AI Quant Platform V2

FastAPI와 React로 만든 로컬 시세 분석 포트폴리오입니다. Bithumb 원화 가상자산과 Yahoo Finance 국내·미국 주식, 한국투자증권 KRX/NXT 선택 조회를 지원합니다. 미국 주식은 정규장·프리마켓·애프터마켓을 선택할 수 있습니다.

## Windows 로컬 실행

Python 3.12와 Node.js 22를 설치하고 저장소 루트의 PowerShell에서 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.main:app
```

다른 PowerShell에서 프런트엔드를 실행한 뒤 http://localhost:5173 에 접속합니다. API 문서는 http://127.0.0.1:8000/docs 에서 볼 수 있습니다.

```powershell
npm.cmd ci --prefix frontend
npm.cmd run dev --prefix frontend
```

## Docker Compose

Docker Compose v2.24 이상에서 `docker compose up --build -d --wait`를 실행하고 http://localhost:3000 에 접속합니다. PostgreSQL에는 가상 잔액과 체결 기록을 저장하며, Redis는 공개 시세를 30초간 캐시합니다. API가 시작할 때 Alembic 마이그레이션을 적용합니다. Windows 로컬 실행의 기본 저장소는 SQLite입니다.

## 분석 및 모의투자

- EMA20/60, Wilder RSI14와 현재 조회 범위 고저점 기준 피보나치 되돌림을 표시합니다.
- AI 분석은 선택한 차트의 캔들과 지표만 읽고 조회 근거와 시각을 표시합니다.
- EMA 교차 백테스트는 신호 다음 봉의 시가에 거래 비용을 적용해 모의 체결합니다. EMA60이 계산될 만큼 데이터가 있어야 교차를 찾을 수 있습니다.
- 모의투자는 시세 출처·종목별 가상 계좌를 사용합니다. 조회된 최근 봉 종가에 수수료 10bp, 슬리피지 5bp를 적용합니다. 앱에는 실제 주문 연동이 없습니다.

## 외부 연동 설정

실제 자격증명은 로컬 `.env`에만 설정합니다. `.env.example`에는 변수 이름만 포함되어 있습니다.

| 기능 | 필요한 설정 | 확인 범위 |
| --- | --- | --- |
| KRX/NXT | `KIS_APP_KEY`, `KIS_APP_SECRET`, 유효한 실전 `KIS_ACCESS_TOKEN` 및 시세 조회 권한 | 모의 HTTP 검증. 일봉·주봉과 최대 30개 당일 1분봉을 지원하며 토큰 갱신은 수동입니다. |
| AI 분석 | `OPENAI_API_KEY`와 `OPENAI_MODEL` 사용 권한 | 모의 도구 호출 검증. |
| Alpaca BOATS | `ENABLE_OVERNIGHT=true`, `ALPACA_API_KEY`, `ALPACA_API_SECRET` 및 BOATS 권한 | 기본 비활성이고 UI에서도 비활성입니다. |

KIS를 선택하면 KRX는 `J`, NXT는 `NX`로 조회합니다. 키 미설정 시 명시적으로 오류를 반환합니다. Yahoo Finance는 별도 선택지입니다. [한국투자증권 공식 API 예제](https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock)

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd run build --prefix frontend
```

GitHub Actions는 Linux와 Windows에서 이 명령에 해당하는 테스트와 빌드를 실행합니다.
