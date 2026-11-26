import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { createChart, CandlestickSeries, ColorType, type UTCTimestamp } from "lightweight-charts";

const markets = {
  crypto: ["BTC-KRW", "ETH-KRW"],
  kr_stock: ["005930", "000660"],
  us_stock: ["NVDA", "TSLA", "AAPL"]
};
type Market = keyof typeof markets;
const labels = { crypto: "가상자산", kr_stock: "국내 주식", us_stock: "미국 주식" };

function App() {
  const [market, setMarket] = useState<Market>("crypto");
  const [symbol, setSymbol] = useState(markets.crypto[0]);
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
    const base = market === "crypto" ? 100000000 : market === "kr_stock" ? 70000 : 150;
    const seed = Array.from(symbol).reduce((a,c) => a+c.charCodeAt(0),0);
    const data = Array.from({length: 100}, (_,i) => {
      const open = base * (1 + i*0.0005 + Math.sin(i/5+seed)*0.015);
      const close = open * (1+Math.sin(i*1.7+seed)*0.006);
      return {time: (1764547200+i*86400) as UTCTimestamp, open, close,
        high: Math.max(open,close)*1.003, low: Math.min(open,close)*0.997};
    });
    series.setData(data);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [market,symbol]);
  return <main style={{maxWidth:1200,margin:"auto",padding:24,fontFamily:"system-ui,sans-serif"}}>
    <h1>AI Quant Platform V2</h1>
    <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
      <label>시장 <select value={market} onChange={e=>{const m=e.target.value as Market;setMarket(m);setSymbol(markets[m][0]);}}>
        {Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>종목 <select value={symbol} onChange={e=>setSymbol(e.target.value)}>
        {markets[market].map(s=><option key={s}>{s}</option>)}
      </select></label>
    </div>
    <p>{symbol} · {market==="us_stock"?"USD":"KRW"} · 예시 데이터 (실제 시세 아님)</p>
    <div ref={host} style={{height:460,width:"100%"}} />
    <section><h2>AI 분석</h2><p>AI 및 실시간 시세 API 연동 예정</p></section>
  </main>;
}
createRoot(document.getElementById("root")!).render(<App />);
