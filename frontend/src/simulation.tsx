import { useEffect, useRef, useState, type FormEvent } from "react";

type Portfolio = { cash: string; units: string; currency: string };
type Backtest = { return_pct: number; final_equity: number; trades: unknown[]; currency: string };
type PendingOrder = { request_id: string; side: string; quantity: string };

async function api<T>(path: string, signal: AbortSignal, order?: PendingOrder): Promise<T> {
  const response = await fetch(path, {
    signal, method: order ? "POST" : "GET",
    ...(order ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(order) } : {}),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "요청 실패");
  return payload;
}

export function Simulation({ base, query, ready }: { base: string; query: string; ready: boolean }) {
  const [portfolio, setPortfolio] = useState<Portfolio>();
  const [backtest, setBacktest] = useState<Backtest>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef(new AbortController());
  const pending = useRef<PendingOrder | undefined>(undefined);
  const paperPath = base + "/paper?" + query;

  useEffect(() => {
    const active = new AbortController();
    controller.current = active;
    api<Portfolio>(paperPath, active.signal).then(setPortfolio).catch(error => {
      if (!active.signal.aborted) setError(error.message);
    });
    return () => active.abort();
  }, [paperPath]);

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    const signal = controller.current.signal;
    setBusy(true);
    setError("");
    try {
      await action(signal);
    } catch (error) {
      if (!signal.aborted) setError(error instanceof Error ? error.message : "요청 실패");
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const side = String(data.get("side"));
    const quantity = String(data.get("quantity"));
    if (pending.current?.side !== side || pending.current.quantity !== quantity) {
      pending.current = { request_id: crypto.randomUUID(), side, quantity };
    }
    const order = pending.current;
    void run(async signal => {
      await api(paperPath, signal, order);
      pending.current = undefined;
      setPortfolio(await api<Portfolio>(paperPath, signal));
    });
  }

  return <section>
    <h2>백테스트 및 모의투자</h2>
    <button disabled={!ready || busy} onClick={() => void run(async signal => {
      setBacktest(await api<Backtest>(base + "/backtest?" + query, signal));
    })}>EMA 교차 백테스트</button>
    {backtest && <p>최종 평가액 {backtest.final_equity.toLocaleString()} {backtest.currency} · 수익률 {backtest.return_pct.toFixed(2)}% · 체결 {backtest.trades.length}건</p>}
    {portfolio && <p>가상 잔액 {Number(portfolio.cash).toLocaleString()} {portfolio.currency} · 보유 {portfolio.units}</p>}
    <form onSubmit={submit}>
      <label>구분 <select name="side"><option value="buy">매수</option><option value="sell">매도</option></select></label>{" "}
      <label>수량 <input type="number" name="quantity" min="0.00000001" step="0.00000001" required /></label>{" "}
      <button disabled={!ready || busy || !portfolio}>모의 체결</button>
    </form>
    <p>최근 조회 봉 종가 기준 · 수수료 10bp · 슬리피지 5bp</p>
    {error && <p role="alert">{error}</p>}
  </section>;
}
