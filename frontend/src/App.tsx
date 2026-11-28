import { useEffect, useMemo, useRef, useState } from "react";
import {
  ExternalLink,
  Search,
  RefreshCw,
  SlidersHorizontal,
  Star,
} from "lucide-react";
import { StockChart, type ChartTimeframe } from "./StockChart";

type Timeframe = "daily" | "4h";
type View = "actionable" | "setups" | "all";

type Stock = {
  Symbol: string;
  Timeframe: string;
  Price: number;
  MA50: number;
  MA150: number;
  MA200: number;
  "MA200 slope %": number;
  "52W High": number;
  "52W Low": number;
  "% Above 52W Low": number;
  "% Below 52W High": number;
  "RS Rating": number;
  Score: number;
  TradingView: string;
  "P > MA50": boolean;
  "P > MA150": boolean;
  "P > MA200": boolean;
  "MA50 > MA150": boolean;
  "MA150 > MA200": boolean;
  "MA200 Rising": boolean;
  "25% Above 52W Low": boolean;
  "Within 25% 52W High": boolean;
  "RS > Threshold": boolean;
  Stage: string | null;
  Setup: string | null;
  "Setup Score": number | null;
  Pivot: number | null;
  Stop: number | null;
  "Risk %": number | null;
  "% From Pivot": number | null;
  "Entry Zone": string | null;
  "Base Start": string | null;
  "Base Bars": number | null;
  "Base Depth %": number | null;
  "Prior Rally %": number | null;
  Contractions: string | null;
  Shakeout: string | null;
  "Volume Dry-up": number | null;
  "Tightness %": number | null;
  "Breakout Date": string | null;
  "Breakout Volume x": number | null;
  "Setup Notes": string | null;
  "1H Stage": string | null;
  "1H Pivot": number | null;
  "1H % From Pivot": number | null;
  "1H Setup Score": number | null;
  "F&O": boolean | null;
  "Lot Size": number | null;
  "Avg Value (Cr)": number | null;
  Liquid: boolean | null;
};

const ACTIONABLE = ["Breakout", "Ready", "Recent breakout"];

const API = "/api";

const VIEWS: { id: View; label: string; stages: string | null }[] = [
  { id: "actionable", label: "Actionable setups", stages: "Breakout,Ready,Recent breakout" },
  {
    id: "setups",
    label: "All setups",
    stages: "Breakout,Ready,Recent breakout,Forming,Extended,Failed",
  },
  { id: "all", label: "All stocks", stages: null },
];

const SETUP_RULES: Record<Timeframe, string[]> = {
  daily: [
    "VCP: ≥25% rally within 3 months into the base",
    "VCP: base 3 weeks – 12 months, ≤20% deep",
    "Power play: ≥25% run within 8 weeks, 2–15 day pause ≤10% deep",
    "Pullbacks tighten from the deepest one; lows rise (shakeouts allowed)",
    "Ready: within 5% (Power play 3%) below the pivot",
    "Breakout: close above pivot; volume ≥1.5× 50-bar average",
  ],
  "4h": [
    "≥15% rally within 60 bars (~30 days) into the base",
    "Base 8 – 150 bars (4 – 75 days), ≤15% deep",
    "Pullbacks tighten from the deepest one; lows rise (shakeouts allowed)",
    "Ready: within 3% below the pivot",
    "Breakout: close above pivot; volume ≥1.5× 50-bar average",
    "Use with the Daily view to time entries",
  ],
};

type SortKey = "setupScore" | "risk" | "fromPivot" | "rs" | "trend";

// `first` is the direction of the first click: best value on top.
const SORT_COLUMNS: Record<SortKey, { field: keyof Stock; first: "asc" | "desc" }> = {
  setupScore: { field: "Setup Score", first: "desc" },
  risk: { field: "Risk %", first: "asc" },
  fromPivot: { field: "% From Pivot", first: "desc" },
  rs: { field: "RS Rating", first: "desc" },
  trend: { field: "Score", first: "desc" },
};

const STAGE_ORDER = ["Breakout", "Ready", "Recent breakout", "Forming", "Extended", "Failed"];

function countBy(stocks: Stock[], pick: (stock: Stock) => string | null) {
  const counts: Record<string, number> = {};
  for (const stock of stocks) {
    const key = pick(stock);
    if (key) counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

function toggleValue(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function FilterChips({
  label,
  options,
  counts,
  selected,
  onToggle,
}: {
  label: string;
  options: string[];
  counts: Record<string, number>;
  selected: string[];
  onToggle: (value: string) => void;
}) {
  const present = options.filter((option) => counts[option] || selected.includes(option));
  if (present.length === 0) return null;
  return (
    <div className="filter-group">
      <span className="filter-label">{label}</span>
      {present.map((option) => (
        <button
          key={option}
          className={`chip ${selected.includes(option) ? "active" : ""}`}
          onClick={() => onToggle(option)}
        >
          {option} <em>{counts[option] ?? 0}</em>
        </button>
      ))}
    </div>
  );
}

function SortHeader({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sort: { key: SortKey; dir: "asc" | "desc" } | null;
  onSort: (key: SortKey) => void;
}) {
  const active = sort?.key === sortKey;
  return (
    <th
      className="sortable"
      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
    >
      <button onClick={() => onSort(sortKey)} title={`Sort by ${label.toLowerCase()}`}>
        {label}
        <span className={active ? "arrow on" : "arrow"}>
          {active ? (sort.dir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </button>
    </th>
  );
}

function HourlyTag({ stock }: { stock: Stock }) {
  const stage = stock["1H Stage"];
  if (!stage || !ACTIONABLE.includes(stage)) return null;
  return (
    <span
      className="tag tag-1h"
      title={`1H power play: ${stage} · pivot ₹${format(stock["1H Pivot"])} (${signed(stock["1H % From Pivot"])})`}
    >
      1H {stage === "Ready" ? "ready" : "BO"}
    </span>
  );
}

function FnoTag({ stock }: { stock: Stock }) {
  if (!stock["F&O"]) return null;
  return (
    <span className="tag tag-fno" title={`F&O stock · lot size ${stock["Lot Size"] ?? "-"}`}>
      F&amp;O
    </span>
  );
}

function format(value: number | null | undefined, digits = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function signed(value: number | null | undefined, digits = 1) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

function Check({ value }: { value: boolean }) {
  return (
    <span className={value ? "check yes" : "check no"}>
      {value ? "✓" : "×"}
    </span>
  );
}

function StageBadge({ stage, notes }: { stage: string | null; notes?: string | null }) {
  if (!stage) return <span className="stage stage-no-base">-</span>;
  const css = stage.toLowerCase().replace(/\s+/g, "-");
  return (
    <span className={`stage stage-${css}`} title={notes ?? undefined}>
      {stage}
      {notes ? " ⚠" : ""}
    </span>
  );
}

function SetupScore({ value }: { value: number | null }) {
  if (typeof value !== "number" || value <= 0) return <span className="setup-score">-</span>;
  const tier = value >= 80 ? "high" : value >= 60 ? "mid" : "low";
  return <span className={`setup-score ${tier}`}>{value}</span>;
}

function App() {
  const [timeframe, setTimeframe] = useState<Timeframe>("daily");
  const [view, setView] = useState<View>("actionable");
  const [minScore, setMinScore] = useState(7);
  const [minRS, setMinRS] = useState(60);
  const [minSetupScore, setMinSetupScore] = useState(0);
  const [liquidOnly, setLiquidOnly] = useState(true);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<string[]>([]);
  const [setupFilter, setSetupFilter] = useState<string[]>([]);
  const [entryFilter, setEntryFilter] = useState<string[]>([]);
  const [shakeoutOnly, setShakeoutOnly] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" } | null>(null);
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Stock | null>(null);
  const [chartTimeframe, setChartTimeframe] = useState<ChartTimeframe>("daily");
  const [watchlist, setWatchlist] = useState<string[]>([]);

  const [showWatchlist, setShowWatchlist] = useState(false);
  const latestRequest = useRef(0);

  async function loadWatchlist() {
    const response = await fetch(`${API}/watchlist`);

    if (!response.ok) {
      throw new Error("Failed to load watchlist");
    }

    const data = await response.json();
    setWatchlist(data.symbols);
  }

  async function toggleWatchlist(symbol: string) {
    const isSaved = watchlist.includes(symbol);

    const response = await fetch(
      `${API}/watchlist/${encodeURIComponent(symbol)}`,
      {
        method: isSaved ? "DELETE" : "POST",
      },
    );

    if (!response.ok) {
      throw new Error("Failed to update watchlist");
    }

    setWatchlist((current) =>
      isSaved
        ? current.filter((item) => item !== symbol)
        : [...current, symbol],
    );
  }

  async function loadStocks() {
    // Filters can change while a request is in flight; only the newest response is applied.
    const requestId = ++latestRequest.current;
    setLoading(true);
    try {
      // Watchlist names stay visible even when they no longer pass the screen.
      const params = new URLSearchParams({
        timeframe,
        min_score: String(showWatchlist ? 0 : minScore),
        min_rs: String(showWatchlist ? 0 : minRS),
        min_setup_score: String(showWatchlist ? 0 : minSetupScore),
        liquid_only: String(!showWatchlist && liquidOnly),
      });

      const stages = VIEWS.find((item) => item.id === view)?.stages;
      if (stages && !showWatchlist) params.set("stages", stages);
      if (search.trim()) params.set("search", search.trim());

      const response = await fetch(`${API}/stocks?${params}`);
      if (!response.ok) throw new Error("API request failed");

      const data = await response.json();
      if (requestId === latestRequest.current) setStocks(data.stocks);
    } finally {
      if (requestId === latestRequest.current) setLoading(false);
    }
  }

  useEffect(() => {
    void loadStocks();
  }, [timeframe, view, minScore, minRS, minSetupScore, liquidOnly, showWatchlist]);

  useEffect(() => {
    void loadWatchlist();
  }, []);

  const visibleStocks = showWatchlist
    ? stocks.filter((stock) => watchlist.includes(stock.Symbol))
    : stocks;

  const stageCounts = useMemo(() => countBy(visibleStocks, (s) => s.Stage), [visibleStocks]);
  const setupCounts = useMemo(() => countBy(visibleStocks, (s) => s.Setup), [visibleStocks]);
  const entryCounts = useMemo(() => countBy(visibleStocks, (s) => s["Entry Zone"]), [visibleStocks]);
  const shakeoutCount = useMemo(
    () => visibleStocks.filter((s) => s.Shakeout).length,
    [visibleStocks],
  );

  const tableStocks = useMemo(() => {
    const matches = (selected: string[], value: string | null) =>
      selected.length === 0 || (value != null && selected.includes(value));

    const rows = visibleStocks.filter(
      (s) =>
        matches(stageFilter, s.Stage) &&
        matches(setupFilter, s.Setup) &&
        matches(entryFilter, s["Entry Zone"]) &&
        (!shakeoutOnly || Boolean(s.Shakeout)),
    );
    if (!sort) return rows;

    const column = SORT_COLUMNS[sort.key].field;
    const direction = sort.dir === "asc" ? 1 : -1;
    // Rows without a value always sink to the bottom.
    return [...rows].sort((a, b) => {
      const x = a[column] as number | null;
      const y = b[column] as number | null;
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x - y) * direction;
    });
  }, [visibleStocks, stageFilter, setupFilter, entryFilter, shakeoutOnly, sort]);

  const filtersActive =
    stageFilter.length + setupFilter.length + entryFilter.length > 0 || shakeoutOnly;

  function clearFilters() {
    setStageFilter([]);
    setSetupFilter([]);
    setEntryFilter([]);
    setShakeoutOnly(false);
  }

  function toggleSort(key: SortKey) {
    setSort((current) => {
      const first = SORT_COLUMNS[key].first;
      if (!current || current.key !== key) return { key, dir: first };
      if (current.dir === first) return { key, dir: first === "asc" ? "desc" : "asc" };
      return null;
    });
  }

  const stats = useMemo(() => {
    const count = (stage: string) => visibleStocks.filter((s) => s.Stage === stage).length;
    const avgRS =
      visibleStocks.length > 0
        ? visibleStocks.reduce((sum, s) => sum + s["RS Rating"], 0) / visibleStocks.length
        : 0;

    return {
      breakout: count("Breakout"),
      ready: count("Ready"),
      recent: count("Recent breakout"),
      avgRS,
    };
  }, [visibleStocks]);

  const viewLabel = showWatchlist
    ? "Watchlist"
    : VIEWS.find((item) => item.id === view)?.label ?? "Stocks";

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="eyebrow">NSE EQUITY RESEARCH</div>
          <h1>Minervini Scanner</h1>
          <p>Trend Template · VCP / Power play setups · Daily / 4H</p>
        </div>

        <button className="refresh" onClick={() => void loadStocks()} disabled={loading}>
          <RefreshCw size={16} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </header>

      <section className="controls">
        <div className="segmented">
          <button
            className={timeframe === "daily" ? "active" : ""}
            onClick={() => setTimeframe("daily")}
          >
            Daily
          </button>
          <button
            className={timeframe === "4h" ? "active" : ""}
            onClick={() => setTimeframe("4h")}
          >
            4H
          </button>
        </div>

        <div className="segmented">
          {VIEWS.map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <label>
          <SlidersHorizontal size={15} />
          Minimum score
          <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
            {[9, 8, 7, 6, 5, 0].map((n) => (
              <option key={n} value={n}>{n}/9</option>
            ))}
          </select>
        </label>

        <label>
          RS ≥
          <input
            type="number"
            min="0"
            max="100"
            value={minRS}
            onChange={(e) => setMinRS(Number(e.target.value))}
          />
        </label>

        <label>
          Setup score ≥
          <input
            type="number"
            min="0"
            max="100"
            value={minSetupScore}
            onChange={(e) => setMinSetupScore(Number(e.target.value))}
          />
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={liquidOnly}
            onChange={(e) => setLiquidOnly(e.target.checked)}
          />
          Liquid only
        </label>

        <div className="search">
          <Search size={16} />
          <input
            placeholder="Search stock..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void loadStocks();
            }}
          />
        </div>

        <button
          className={`watchlist-toggle ${showWatchlist ? "active" : ""}`}
          onClick={() => setShowWatchlist((current) => !current)}
        >
          <Star size={15} />
          Watchlist ({watchlist.length})
        </button>
      </section>

      <section className="checklist-card">
        <div className="checklist-header">
          <div>
            <div className="eyebrow">SCREENING RULES</div>
            <h2>Trend Template + Setup Detection</h2>
          </div>

          <span className="threshold-badge">
            Trend score ≥ {minScore}/9 · RS ≥ {minRS}
          </span>
        </div>

        <div className="template-rules">
          <div>✓ Price &gt; MA50, MA150, MA200</div>
          <div>✓ MA50 &gt; MA150 &gt; MA200, MA200 rising</div>
          <div>✓ ≥25% above 52W low, within 25% of 52W high</div>
          {SETUP_RULES[timeframe].map((rule) => (
            <div key={rule}>◆ {rule}</div>
          ))}
        </div>

        <div className="checklist-note">
          Tags: <b>F&amp;O</b> = stock has NSE derivatives (hover for lot size) · <b>1H</b> =
          1H power play (≥8% run, 4–35 bar pause ≤5% deep) is ready or breaking out — a hint
          only · <b>SO</b> = shakeout in the base.
          <br />
          Liquid = 50-day average traded value ≥ ₹5 Cr and price ≥ ₹30. Setup score (0–100)
          rewards tightening pullbacks, a tight final contraction, volume dry-up, a strong
          prior rally, proximity to the pivot and shakeouts.
        </div>
      </section>

      <section className="stats">
        <div className="stat">
          <span>{viewLabel}</span>
          <strong>{visibleStocks.length}</strong>
        </div>
        <div className="stat">
          <span>Breakout today</span>
          <strong>{stats.breakout}</strong>
        </div>
        <div className="stat">
          <span>Ready (near pivot)</span>
          <strong>{stats.ready}</strong>
        </div>
        <div className="stat">
          <span>Recent breakout</span>
          <strong>{stats.recent}</strong>
        </div>
        <div className="stat">
          <span>Average RS</span>
          <strong>{format(stats.avgRS, 1)}</strong>
        </div>
      </section>

      <main className="table-card">
        <div className="table-header">
          <div>
            <h2>{viewLabel}</h2>
            <span>
              {timeframe === "daily" ? "Daily candles" : "4-hour candles"} · ranked by stage,
              then setup score (click a header to sort) · ⚠ = breakout volume below 1.5× average
            </span>
          </div>
        </div>

        {!loading && visibleStocks.length > 0 && (
          <div className="filter-bar">
            <FilterChips
              label="Stage"
              options={STAGE_ORDER}
              counts={stageCounts}
              selected={stageFilter}
              onToggle={(v) => setStageFilter((list) => toggleValue(list, v))}
            />
            <FilterChips
              label="Setup"
              options={["VCP", "Power play"]}
              counts={setupCounts}
              selected={setupFilter}
              onToggle={(v) => setSetupFilter((list) => toggleValue(list, v))}
            />
            <FilterChips
              label="Entry"
              options={["Cheat", "Low cheat", "Handle"]}
              counts={entryCounts}
              selected={entryFilter}
              onToggle={(v) => setEntryFilter((list) => toggleValue(list, v))}
            />
            <div className="filter-group">
              <span className="filter-label">Pullbacks</span>
              <button
                className={`chip ${shakeoutOnly ? "active" : ""}`}
                onClick={() => setShakeoutOnly((on) => !on)}
              >
                Shakeout (SO) <em>{shakeoutCount}</em>
              </button>
            </div>
            {filtersActive && (
              <button className="chip clear" onClick={clearFilters}>
                Clear filters
              </button>
            )}
            <span className="filter-count">
              {tableStocks.length} of {visibleStocks.length}
            </span>
          </div>
        )}

        {loading ? (
          <div className="empty">Loading scanner results...</div>
        ) : visibleStocks.length === 0 ? (
          <div className="empty">
            No stocks match the current filters. Run the scanner first.
          </div>
        ) : tableStocks.length === 0 ? (
          <div className="empty">No stocks match the stage / setup filters above.</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Stage</th>
                  <th>Setup</th>
                  <SortHeader label="Setup score" sortKey="setupScore" sort={sort} onSort={toggleSort} />
                  <th>Pivot</th>
                  <SortHeader label="From pivot" sortKey="fromPivot" sort={sort} onSort={toggleSort} />
                  <th>Stop</th>
                  <SortHeader label="Risk" sortKey="risk" sort={sort} onSort={toggleSort} />
                  <th>Pullbacks %</th>
                  <th>Base</th>
                  <SortHeader label="Trend" sortKey="trend" sort={sort} onSort={toggleSort} />
                  <SortHeader label="RS" sortKey="rs" sort={sort} onSort={toggleSort} />
                  <th>Price</th>
                  <th>52W high</th>
                  <th>Checklist</th>
                  <th>Chart</th>
                </tr>
              </thead>
              <tbody>
                {tableStocks.map((stock) => (
                  <tr key={stock.Symbol}>
                    <td>
                      <div className="stock-name">
                        <button
                          className="symbol"
                          onClick={() => {
                            setChartTimeframe(timeframe);
                            setSelected(stock);
                          }}
                        >
                          {stock.Symbol}
                        </button>
                        <FnoTag stock={stock} />

                        <button
                          className={`star-button ${
                            watchlist.includes(stock.Symbol) ? "saved" : ""
                          }`}
                          onClick={() => toggleWatchlist(stock.Symbol)}
                          title={
                            watchlist.includes(stock.Symbol)
                              ? "Remove from watchlist"
                              : "Add to watchlist"
                          }
                        >
                          <Star
                            size={14}
                            fill={watchlist.includes(stock.Symbol) ? "currentColor" : "none"}
                          />
                        </button>
                      </div>
                    </td>
                    <td>
                      <StageBadge stage={stock.Stage} notes={stock["Setup Notes"]} />
                      <HourlyTag stock={stock} />
                    </td>
                    <td className="muted">
                      {stock.Setup ?? "-"}
                      {stock["Entry Zone"] ? ` · ${stock["Entry Zone"]}` : ""}
                    </td>
                    <td>
                      <SetupScore value={stock["Setup Score"]} />
                    </td>
                    <td>{stock.Pivot ? `₹${format(stock.Pivot)}` : "-"}</td>
                    <td>{signed(stock["% From Pivot"])}</td>
                    <td>{stock.Stop ? `₹${format(stock.Stop)}` : "-"}</td>
                    <td>{stock["Risk %"] != null ? `${format(stock["Risk %"], 1)}%` : "-"}</td>
                    <td className="contractions">
                      {stock.Contractions ?? "-"}
                      {stock.Shakeout ? <span className="shakeout" title={`Shakeout ${stock.Shakeout}`}>SO</span> : null}
                    </td>
                    <td className="muted">
                      {stock["Base Bars"] != null
                        ? `${stock["Base Bars"]} bars · ${format(stock["Base Depth %"], 1)}%`
                        : "-"}
                    </td>
                    <td>
                      <span className={`score score-${stock.Score}`}>
                        {stock.Score}/9
                      </span>
                    </td>
                    <td className="rs">{format(stock["RS Rating"], 1)}</td>
                    <td>₹{format(stock.Price)}</td>
                    <td>-{format(stock["% Below 52W High"], 1)}%</td>
                    <td>
                      <div className="checks">
                        <Check value={stock["P > MA50"]} />
                        <Check value={stock["P > MA150"]} />
                        <Check value={stock["P > MA200"]} />
                        <Check value={stock["MA50 > MA150"]} />
                        <Check value={stock["MA150 > MA200"]} />
                        <Check value={stock["MA200 Rising"]} />
                        <Check value={stock["25% Above 52W Low"]} />
                        <Check value={stock["Within 25% 52W High"]} />
                        <Check value={stock["RS > Threshold"]} />
                      </div>
                    </td>
                    <td>
                      <a href={stock.TradingView} target="_blank" rel="noreferrer">
                        <ExternalLink size={15} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-top">
              <div>
                <div className="eyebrow">SETUP & TREND TEMPLATE</div>
                <h2>
                  {selected.Symbol} <FnoTag stock={selected} />
                </h2>
              </div>
              <button className="close" onClick={() => setSelected(null)}>×</button>
            </div>

            <div className="chart-toolbar">
              <div className="segmented">
                {(["daily", "4h"] as const).map((item) => (
                  <button
                    key={item}
                    className={chartTimeframe === item ? "active" : ""}
                    onClick={() => setChartTimeframe(item)}
                  >
                    {item === "daily" ? "Daily" : "4H"}
                  </button>
                ))}
              </div>
              <span className="muted">
                Setup lines are recomputed from the latest cached bars for the selected timeframe.
              </span>
            </div>
            <StockChart symbol={selected.Symbol} timeframe={chartTimeframe} />

            <div className="modal-stage">
              <StageBadge stage={selected.Stage} notes={selected["Setup Notes"]} />
              <span className="muted">
                {selected.Setup ?? "No setup"}
                {selected["Entry Zone"] ? ` · pivot in ${selected["Entry Zone"].toLowerCase()} zone` : ""}
              </span>
              <SetupScore value={selected["Setup Score"]} />
            </div>

            <div className="detail-grid">
              <div><span>Price</span><strong>₹{format(selected.Price)}</strong></div>
              <div><span>Pivot</span><strong>{selected.Pivot ? `₹${format(selected.Pivot)}` : "-"}</strong></div>
              <div><span>Stop (last contraction low)</span><strong>{selected.Stop ? `₹${format(selected.Stop)}` : "-"}</strong></div>
              <div><span>From pivot</span><strong>{signed(selected["% From Pivot"])}</strong></div>
              <div>
                <span>Risk to stop</span>
                <strong>{selected["Risk %"] != null ? `${format(selected["Risk %"], 1)}%` : "-"}</strong>
              </div>
              <div><span>Prior rally</span><strong>{signed(selected["Prior Rally %"])}</strong></div>
              <div><span>Base start</span><strong>{selected["Base Start"] ?? "-"}</strong></div>
              <div>
                <span>Base length / depth</span>
                <strong>
                  {selected["Base Bars"] != null
                    ? `${selected["Base Bars"]} bars · ${format(selected["Base Depth %"], 1)}%`
                    : "-"}
                </strong>
              </div>
              <div><span>Pullbacks %</span><strong>{selected.Contractions ?? "-"}</strong></div>
              <div><span>Shakeout</span><strong>{selected.Shakeout ?? "-"}</strong></div>
              <div>
                <span>Volume dry-up (10/50)</span>
                <strong>{format(selected["Volume Dry-up"])}×</strong>
              </div>
              <div><span>Final tightness</span><strong>{format(selected["Tightness %"], 1)}%</strong></div>
              <div><span>Breakout</span><strong>{selected["Breakout Date"] ?? "-"}</strong></div>
              <div>
                <span>Breakout volume</span>
                <strong>
                  {selected["Breakout Volume x"] != null
                    ? `${format(selected["Breakout Volume x"])}×`
                    : "-"}
                </strong>
              </div>
              <div><span>Avg value</span><strong>₹{format(selected["Avg Value (Cr)"], 1)} Cr</strong></div>
              <div>
                <span>F&amp;O lot size</span>
                <strong>{selected["F&O"] ? selected["Lot Size"] : "Not in F&O"}</strong>
              </div>
              <div>
                <span>1H power play</span>
                <strong>
                  {selected["1H Stage"] ?? "-"}
                  {selected["1H Pivot"] ? ` · ₹${format(selected["1H Pivot"])}` : ""}
                </strong>
              </div>
              <div><span>RS Rating</span><strong>{format(selected["RS Rating"], 1)}</strong></div>
              <div><span>Trend score</span><strong>{selected.Score}/9</strong></div>
              <div><span>200MA slope</span><strong>{format(selected["MA200 slope %"])}%</strong></div>
            </div>

            <div className="checklist">
              {[
                ["Price > MA50", selected["P > MA50"]],
                ["Price > MA150", selected["P > MA150"]],
                ["Price > MA200", selected["P > MA200"]],
                ["MA50 > MA150", selected["MA50 > MA150"]],
                ["MA150 > MA200", selected["MA150 > MA200"]],
                ["MA200 rising", selected["MA200 Rising"]],
                [">25% above 52W low", selected["25% Above 52W Low"]],
                ["Within 25% of 52W high", selected["Within 25% 52W High"]],
                ["RS > threshold", selected["RS > Threshold"]],
              ].map(([label, value]) => (
                <div className="rule" key={String(label)}>
                  <span>{String(label)}</span>
                  <Check value={Boolean(value)} />
                </div>
              ))}
            </div>

            <button
              className="watchlist-modal-button"
              onClick={() => toggleWatchlist(selected.Symbol)}
            >
              <Star
                size={16}
                fill={watchlist.includes(selected.Symbol) ? "currentColor" : "none"}
              />

              {watchlist.includes(selected.Symbol)
                ? "Remove from Watchlist"
                : "Add to Watchlist"}
            </button>

            <a className="chart-button" href={selected.TradingView} target="_blank" rel="noreferrer">
              Open TradingView <ExternalLink size={16} />
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
