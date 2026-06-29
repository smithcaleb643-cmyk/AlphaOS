import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
} from "lightweight-charts";

function AlphaLiveChart() {
  const chartBoxRef = useRef(null);
  const [hud, setHud] = useState({
    symbol: "SOL/USD",
    price: "Loading...",
    change: "0.00%",
    status: "Connecting",
  });

  useEffect(() => {
    if (!chartBoxRef.current) return;

    const chart = createChart(chartBoxRef.current, {
      width: chartBoxRef.current.clientWidth,
      height: 320,
      layout: {
        background: { color: "#050914" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.06)" },
        horzLines: { color: "rgba(148, 163, 184, 0.06)" },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const priceLines = [];

    function addLine(price, color, title) {
      const line = candleSeries.createPriceLine({
        price,
        color,
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title,
      });
      priceLines.push(line);
    }

    function buildCandles(livePrice) {
      const now = Math.floor(Date.now() / 1000);
      const candles = [];
      const volumes = [];

      for (let i = 45; i >= 0; i--) {
        const time = now - i * 120;
        const wave = Math.sin(i / 4) * livePrice * 0.004;
        const open = livePrice + wave;
        const close = livePrice + Math.cos(i / 5) * livePrice * 0.003;
        const high = Math.max(open, close) + livePrice * 0.0017;
        const low = Math.min(open, close) - livePrice * 0.0017;

        candles.push({ time, open, high, low, close });

        volumes.push({
          time,
          value: 50000 + Math.round(Math.abs(Math.sin(i / 2)) * 100000),
          color:
            close >= open
              ? "rgba(34, 197, 94, 0.35)"
              : "rgba(239, 68, 68, 0.35)",
        });
      }

      return { candles, volumes };
    }

    async function loadChart() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/market/summary/So11111111111111111111111111111111111111112"
        );

        const data = await response.json();
        const livePrice = Number(data.price_usd);

        if (!livePrice) return;

        const { candles, volumes } = buildCandles(livePrice);

        candleSeries.setData(candles);
        volumeSeries.setData(volumes);

        priceLines.forEach((line) => candleSeries.removePriceLine(line));
        priceLines.length = 0;

        addLine(livePrice * 0.995, "#3b82f6", "ENTRY");
        addLine(livePrice * 0.92, "#ef4444", "STOP");
        addLine(livePrice * 1.12, "#22c55e", "TP1");
        addLine(livePrice * 1.24, "#22c55e", "TP2");
        addLine(livePrice * 1.45, "#22c55e", "TP3");

        chart.timeScale().fitContent();

        const change = Number(data.price_change?.h24 || 0);

        setHud({
          symbol: `${data.base_token?.symbol || "SOL"}/${data.quote_token?.symbol || "USD"}`,
          price: `$${livePrice.toFixed(4)}`,
          change: `${change.toFixed(2)}%`,
          status: "Live",
        });
      } catch (error) {
        console.error(error);
        setHud({
          symbol: "SOL/USD",
          price: "Error",
          change: "0.00%",
          status: "Error",
        });
      }
    }

    loadChart();
    const timer = setInterval(loadChart, 10000);

    return () => {
      clearInterval(timer);
      chart.remove();
    };
  }, []);

  return (
    <div className="alpha-chart-wrap">
      <div className="chart-hud">
        <div>
          <span className="live-dot">● LIVE</span>
          <strong>{hud.symbol}</strong>
        </div>
        <div>
          <span>Price</span>
          <strong>{hud.price}</strong>
        </div>
        <div>
          <span>24h</span>
          <strong className={hud.change.startsWith("-") ? "red" : "green"}>
            {hud.change}
          </strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{hud.status}</strong>
        </div>
      </div>

      <div className="live-chart" ref={chartBoxRef}></div>
    </div>
  );
}

export default AlphaLiveChart;