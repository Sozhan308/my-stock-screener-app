import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";

export type ChartTimeframe = "daily" | "4h";

type ChartTime = string | number;

type Candle = {
  time: ChartTime;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type Contraction = {
  highTime: ChartTime;
  high: number;
  lowTime: ChartTime;
  low: number;
  depthPct: number;
  shakeout: boolean;
};

type ChartData = {
  symbol: string;
  timeframe: ChartTimeframe;
  candles: Candle[];
  lines: Record<string, { time: ChartTime; value: number }[]>;
  setup: {
    stage: string;
    setupType: string | null;
    score: number;
    breakoutTime: ChartTime | null;
    notes: string[];
    base: null | {
      start: ChartTime;
      high: number;
      low: number;
      pivot: number;
      stop: number;
      contractions: Contraction[];
    };
  };
};

const LINE_COLORS: Record<string, string> = {
  EMA10: "#3b82f6",
  EMA20: "#ef4444",
  SMA50: "#38bdf8",
  SMA150: "#22c55e",
  SMA200: "#f97316",
};

const IST_TIME = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const IST_DAY = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
});

function order(time: ChartTime): number {
  return typeof time === "number" ? time : Date.parse(time) / 1000;
}

function asTime(time: ChartTime): Time {
  return time as Time;
}

function volumeAverage(candles: Candle[], period = 50) {
  const points: { time: Time; value: number }[] = [];
  let sum = 0;
  candles.forEach((candle, index) => {
    sum += candle.volume;
    if (index >= period) sum -= candles[index - period].volume;
    if (index >= period - 1) points.push({ time: asTime(candle.time), value: sum / period });
  });
  return points;
}

function drawChart(container: HTMLElement, data: ChartData) {
  const intraday = data.timeframe === "4h";
  const chart = createChart(container, {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: "#0f141b" },
      textColor: "#9aa5b1",
      fontSize: 11,
      panes: { separatorColor: "#29313b" },
    },
    grid: {
      vertLines: { color: "#161c24" },
      horzLines: { color: "#161c24" },
    },
    rightPriceScale: { borderColor: "#29313b" },
    timeScale: {
      borderColor: "#29313b",
      timeVisible: intraday,
      rightOffset: 6,
      // Intraday bars are UTC timestamps; label them in IST.
      tickMarkFormatter: intraday
        ? (time: Time, tickMarkType: number) => {
            const date = new Date((time as number) * 1000);
            return tickMarkType >= 3 ? IST_TIME.format(date).split(", ")[1] : IST_DAY.format(date);
          }
        : undefined,
    },
    localization: intraday
      ? { timeFormatter: (time: Time) => IST_TIME.format(new Date((time as number) * 1000)) }
      : undefined,
  });

  const candles = chart.addSeries(CandlestickSeries, {
    upColor: "#26a69a",
    downColor: "#ef5350",
    wickUpColor: "#26a69a",
    wickDownColor: "#ef5350",
    borderVisible: false,
  });
  candles.setData(
    data.candles.map((c) => ({
      time: asTime(c.time),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    })),
  );

  for (const [name, points] of Object.entries(data.lines)) {
    chart
      .addSeries(LineSeries, {
        color: LINE_COLORS[name] ?? "#9aa5b1",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      .setData(points.map((p) => ({ time: asTime(p.time), value: p.value })));
  }

  const volume = chart.addSeries(
    HistogramSeries,
    { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false },
    1,
  );
  volume.setData(
    data.candles.map((c) => ({
      time: asTime(c.time),
      value: c.volume,
      color: c.close >= c.open ? "rgba(38,166,154,.55)" : "rgba(239,83,80,.55)",
    })),
  );
  chart
    .addSeries(
      LineSeries,
      {
        color: "#5b8def",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      },
      1,
    )
    .setData(volumeAverage(data.candles));
  chart.panes()[1]?.setHeight(90);

  const base = data.setup.base;
  const markers: SeriesMarker<Time>[] = [];

  if (base) {
    const inBase = data.candles.filter((c) => order(c.time) >= order(base.start));
    for (const [level, color] of [
      [base.high, "rgba(242,201,76,.7)"],
      [base.low, "rgba(242,201,76,.7)"],
    ] as const) {
      chart
        .addSeries(LineSeries, {
          color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        })
        .setData(inBase.map((c) => ({ time: asTime(c.time), value: level })));
    }

    const swings = base.contractions.flatMap((c) => [
      { time: c.highTime, value: c.high },
      { time: c.lowTime, value: c.low },
    ]);
    const zigzag = swings.filter(
      (point, index) => index === 0 || order(point.time) > order(swings[index - 1].time),
    );
    chart
      .addSeries(LineSeries, {
        color: "#f2c94c",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      .setData(zigzag.map((p) => ({ time: asTime(p.time), value: p.value })));

    candles.createPriceLine({
      price: base.pivot,
      color: "#57d675",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Pivot",
    });
    candles.createPriceLine({
      price: base.stop,
      color: "#f06a6a",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Stop",
    });

    markers.push({
      time: asTime(base.start),
      position: "aboveBar",
      shape: "arrowDown",
      color: "#9aa5b1",
      text: "Base",
    });
    for (const c of base.contractions) {
      markers.push({
        time: asTime(c.lowTime),
        position: "belowBar",
        shape: c.shakeout ? "arrowUp" : "circle",
        color: c.shakeout ? "#e3a943" : "#f2c94c",
        text: `${c.shakeout ? "SO " : ""}-${c.depthPct.toFixed(1)}%`,
      });
    }
  }

  if (data.setup.breakoutTime != null) {
    markers.push({
      time: asTime(data.setup.breakoutTime),
      position: "belowBar",
      shape: "arrowUp",
      color: "#57d675",
      text: "Breakout",
    });
  }

  markers.sort((a, b) => order(a.time as ChartTime) - order(b.time as ChartTime));
  createSeriesMarkers(candles, markers);
  chart.timeScale().fitContent();
  return chart;
}

export function StockChart({
  symbol,
  timeframe,
}: {
  symbol: string;
  timeframe: ChartTimeframe;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<ChartData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    setData(null);
    setError(null);
    fetch(`/api/chart/${encodeURIComponent(symbol)}?timeframe=${timeframe}`)
      .then(async (response) => {
        if (!response.ok) throw new Error((await response.json()).detail ?? "Chart failed");
        return response.json() as Promise<ChartData>;
      })
      .then((json) => {
        if (!ignore) setData(json);
      })
      .catch((err: Error) => {
        if (!ignore) setError(err.message);
      });
    return () => {
      ignore = true;
    };
  }, [symbol, timeframe]);

  useEffect(() => {
    if (!data || !container.current) return;
    const chart = drawChart(container.current, data);
    return () => chart.remove();
  }, [data]);

  return (
    <div className="chart-wrap">
      <div className="chart-legend">
        {Object.entries(LINE_COLORS).map(([name, color]) => (
          <span key={name}>
            <i style={{ background: color }} />
            {name}
          </span>
        ))}
        <span><i style={{ background: "#f2c94c" }} />Pullbacks</span>
        <span><i className="dashed" style={{ borderColor: "#f2c94c" }} />Base</span>
        <span><i className="dashed" style={{ borderColor: "#57d675" }} />Pivot</span>
        <span><i className="dashed" style={{ borderColor: "#f06a6a" }} />Stop</span>
      </div>
      {error ? (
        <div className="chart-status">{error}</div>
      ) : !data ? (
        <div className="chart-status">Loading chart…</div>
      ) : null}
      <div ref={container} className="chart-canvas" />
    </div>
  );
}
