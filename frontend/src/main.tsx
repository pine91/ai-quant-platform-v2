import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { createChart, CandlestickSeries, ColorType, type UTCTimestamp } from "lightweight-charts";

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
  const [status, setStatus] = useState("조회 중");
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
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
    const controller = new AbortController();
    setStatus("조회 중");
    fetch("/api/markets/" + market + "/candles?" + new URLSearchParams({symbol, timeframe}), {signal: controller.signal})
      .then(async response => { if (!response.ok) throw new Error("시세 조회 실패 (" + response.status + ")"); return response.json(); })
      .then(result => {
        if (controller.signal.aborted) return;
        series.setData(result.candles.map((c: {time:number;open:number;high:number;low:number;close:number}) => ({...c,time:c.time as UTCTimestamp})));
        chart.timeScale().fitContent();
        setStatus(result.candles.length ? "시세 조회 완료" : "조회 데이터 없음");
      }).catch(error => { if (!controller.signal.aborted) setStatus(String(error.message)); });
    return () => { controller.abort(); chart.remove(); };
  }, [market,symbol,timeframe]);
  return <main style={{maxWidth:1200,margin:"auto",padding:24,fontFamily:"system-ui,sans-serif"}}>
    <h1>AI Quant Platform V2</h1>
    <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
      <label>시장 <select value={market} onChange={e=>{const m=e.target.value as Market;setMarket(m);setSymbol(markets[m][0]);if(m!=="crypto" && timeframe==="4h")setTimeframe("5m");}}>
        {Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>종목 <select value={symbol} onChange={e=>setSymbol(e.target.value)}>
        {markets[market].map(s=><option key={s}>{s}</option>)}
      </select></label>
      <label>시간대 <select value={timeframe} onChange={e=>setTimeframe(e.target.value)}>{["1m","5m","15m","30m","1h","4h","1d","1w"].map(t=><option key={t} value={t} disabled={t==="4h" && market!=="crypto"}>{t}</option>)}</select></label>
    </div>
    <p>{symbol} · {market==="us_stock"?"USD":"KRW"} · {timeframe} · {status}</p>
    <div ref={host} style={{height:460,width:"100%"}} />
    <section><h2>AI 분석</h2><p>AI 및 실시간 시세 API 연동 예정</p></section>
  </main>;
}
createRoot(document.getElementById("root")!).render(<App />);
