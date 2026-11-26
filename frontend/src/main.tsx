import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Simulation } from "./simulation";
import { createChart, CandlestickSeries, LineSeries, ColorType, type UTCTimestamp } from "lightweight-charts";

const markets = {
  crypto: ["BTC-KRW", "ETH-KRW"],
  kr_stock: ["005930", "000660", "247540.KQ", "086520.KQ"],
  us_stock: ["NVDA", "TSLA", "AAPL"]
};
type Market = keyof typeof markets;
const labels = { crypto: "가상자산", kr_stock: "국내 주식", us_stock: "미국 주식" };

function App() {
  const [market, setMarket] = useState<Market>("crypto");
  const [symbol, setSymbol] = useState(markets.crypto[0]);
  const [timeframe, setTimeframe] = useState("5m");
  const [session, setSession] = useState("regular");
  const [venue, setVenue] = useState("");
  const [status, setStatus] = useState("조회 중");
  const [analysis, setAnalysis] = useState<{summary: string; evidence: {data_time: string; last_candle: {close: number}; currency: string}}>();
  const [analysisStatus, setAnalysisStatus] = useState("");
  const analysisRequest = useRef<AbortController | null>(null);
  const query = new URLSearchParams({symbol, timeframe, session, ...(venue ? {venue} : {})});
  async function requestAnalysis() {
    analysisRequest.current?.abort();
    const controller = new AbortController();
    analysisRequest.current = controller;
    setAnalysis(undefined);
    setAnalysisStatus("분석 중");
    try {
      const response = await fetch("/api/markets/" + market + "/analysis?" + query, {
        method: "POST", signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "분석 실패");
      if (!controller.signal.aborted) {
        setAnalysis(result);
        setAnalysisStatus("");
      }
    } catch (error) {
      if (!controller.signal.aborted) setAnalysisStatus(error instanceof Error ? error.message : "분석 실패");
    }
  }
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setAnalysis(undefined);
    setAnalysisStatus("");
    if (!host.current) return;
    const chart = createChart(host.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "#101014" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#222630" }, horzLines: { color: "#222630" } },
      timeScale: { timeVisible: true }
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#ef4444", downColor: "#2563eb", borderVisible: false,
      wickUpColor: "#ef4444", wickDownColor: "#2563eb"
    });
    const ema20 = chart.addSeries(LineSeries, {color: "#fbbf24", lineWidth: 1, title: "EMA20"});
    const ema60 = chart.addSeries(LineSeries, {color: "#a78bfa", lineWidth: 1, title: "EMA60"});
    const rsi = chart.addSeries(LineSeries, {color: "#22c55e", lineWidth: 1, title: "RSI14"}, 1);
    rsi.createPriceLine({price: 30, color: "#64748b", lineWidth: 1, title: "30"});
    rsi.createPriceLine({price: 70, color: "#64748b", lineWidth: 1, title: "70"});
    const controller = new AbortController();
    setStatus("조회 중");
    fetch("/api/markets/" + market + "/candles?" + query, {signal: controller.signal})
      .then(async response => { if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(typeof error?.detail === "string" ? error.detail : "시세 조회 실패 (" + response.status + ")");
      }
      return response.json(); })
      .then(result => {
        if (controller.signal.aborted) return;
        series.setData(result.candles.map((c: {time:number;open:number;high:number;low:number;close:number}) => ({...c,time:c.time as UTCTimestamp})));
        ema20.setData(result.indicators.ema20);
        ema60.setData(result.indicators.ema60);
        rsi.setData(result.indicators.rsi14);
        for (const level of result.indicators.fibonacci) {
          series.createPriceLine({
            price: level.value, color: "#64748b", lineWidth: 1,
            title: `Fib ${level.ratio * 100}%`, axisLabelVisible: false,
          });
        }
        chart.timeScale().fitContent();
        setStatus(result.candles.length ? "시세 조회 완료" : "조회 데이터 없음");
      }).catch(error => { if (!controller.signal.aborted) setStatus(String(error.message)); });
    return () => { controller.abort(); analysisRequest.current?.abort(); chart.remove(); };
  }, [market,symbol,timeframe,session,venue]);
  return <main style={{maxWidth:1200,margin:"auto",padding:24,fontFamily:"system-ui,sans-serif"}}>
    <h1>AI Quant Platform V2</h1>
    <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
      <label>시장 <select value={market} onChange={e=>{const m=e.target.value as Market;setMarket(m);setSymbol(markets[m][0]);setSession("regular");setVenue("");}}>
        {Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>종목 <select value={symbol} onChange={e=>setSymbol(e.target.value)}>
        {markets[market].map(s=><option key={s}>{s}</option>)}
      </select></label>
      <label>시간대 <select value={timeframe} onChange={e=>setTimeframe(e.target.value)}>{["1m","5m","15m","30m","1h","4h","1d","1w"].map(t=><option key={t} value={t} disabled={venue ? !["1m","1d","1w"].includes(t) : session!=="regular" && !["1m","5m","15m","30m"].includes(t)}>{t}</option>)}</select></label>
      {market === "kr_stock" && <label>시세 출처 <select value={venue} onChange={e => {
        setVenue(e.target.value);
        if (e.target.value && !["1m", "1d", "1w"].includes(timeframe)) setTimeframe("1m");
      }}><option value="">Yahoo Finance</option><option value="krx">KRX</option><option value="nxt">NXT</option></select></label>}
      {market==="us_stock" && <label>거래 세션 <select value={session} onChange={e=>{setSession(e.target.value);if(e.target.value!=="regular" && !["1m","5m","15m","30m"].includes(timeframe))setTimeframe("5m");}}><option value="regular">정규장</option><option value="pre">프리마켓</option><option value="post">애프터마켓</option><option value="overnight" disabled>오버나이트 (비활성)</option></select></label>}
    </div>
    <p>{symbol} · {market==="us_stock"?"USD":"KRW"} · {timeframe} · {status}</p>
    <div ref={host} style={{height:460,width:"100%"}} />
    <section><h2>AI 분석</h2>
      <button onClick={requestAnalysis} disabled={status !== "시세 조회 완료" || analysisStatus === "분석 중"}>차트 분석</button>
      <p role="status">{analysisStatus}</p>
      {analysis && <>
        <p>근거 시각 {new Date(analysis.evidence.data_time).toLocaleString()} · 종가 {analysis.evidence.last_candle.close} {analysis.evidence.currency}</p>
        <p style={{whiteSpace: "pre-wrap"}}>{analysis.summary}</p>
      </>}
    </section>
    <Simulation key={market + query.toString()} base={"/api/markets/" + market} query={query.toString()} ready={status === "시세 조회 완료"} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<App />);
