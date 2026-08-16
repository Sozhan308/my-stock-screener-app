import { useEffect, useMemo, useState } from "react";
import {
  ExternalLink,
  Search,
  RefreshCw,
  SlidersHorizontal,
  Star,
} from "lucide-react";

type Timeframe = "daily" | "4h";

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
};

const API = "/api";

function format(value: number, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function Check({ value }: { value: boolean }) {
  return (
    <span className={value ? "check yes" : "check no"}>
      {value ? "✓" : "×"}
    </span>
  );
}

function App() {
  const [timeframe, setTimeframe] = useState<Timeframe>("daily");
  const [minScore, setMinScore] = useState(7);
  const [minRS, setMinRS] = useState(70);
  const [search, setSearch] = useState("");
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Stock | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("minervini-watchlist") || "[]");
    } catch {
      return [];
    }
  });

  const [showWatchlist, setShowWatchlist] = useState(false);

  function toggleWatchlist(symbol: string) {
    setWatchlist((current) => {
      const updated = current.includes(symbol)
        ? current.filter((item) => item !== symbol)
        : [...current, symbol];

      localStorage.setItem("minervini-watchlist", JSON.stringify(updated));

      return updated;
    });
  }
  async function loadStocks() {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        timeframe,
        min_score: String(minScore),
        min_rs: String(minRS),
      });

      if (search.trim()) params.set("search", search.trim());

      const response = await fetch(`${API}/stocks?${params}`);
      if (!response.ok) throw new Error("API request failed");

      const data = await response.json();
      setStocks(data.stocks);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadStocks();
  }, [timeframe, minScore, minRS]);

  const stats = useMemo(() => {
    const nine = stocks.filter((s) => s.Score === 9).length;
    const eight = stocks.filter((s) => s.Score === 8).length;
    const seven = stocks.filter((s) => s.Score === 7).length;
    const avgRS =
      stocks.length > 0
        ? stocks.reduce((sum, s) => sum + s["RS Rating"], 0) / stocks.length
        : 0;

    return { nine, eight, seven, avgRS };
  }, [stocks]);

  const visibleStocks = showWatchlist
    ? stocks.filter((stock) => watchlist.includes(stock.Symbol))
    : stocks;

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="eyebrow">NSE EQUITY RESEARCH</div>
          <h1>Minervini Scanner</h1>
          <p>Trend Template · Relative Strength · Daily / 4H</p>
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

        <label>
          <SlidersHorizontal size={15} />
          Minimum score
          <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
            {[9, 8, 7].map((n) => (
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
            <h2>Minervini Trend Template</h2>
          </div>

          <span className="threshold-badge">
            Qualifies ≥ 7/9
          </span>
        </div>

        <div className="template-rules">
          <div>✓ Price &gt; MA50</div>
          <div>✓ Price &gt; MA150</div>
          <div>✓ Price &gt; MA200</div>
          <div>✓ MA50 &gt; MA150</div>
          <div>✓ MA150 &gt; MA200</div>
          <div>✓ MA200 Rising</div>
          <div>✓ ≥25% above 52W Low</div>
          <div>✓ Within 25% of 52W High</div>
          <div>✓ RS Rating ≥ 70</div>
        </div>

        <div className="checklist-note">
          A stock is included in the candidate list when it satisfies at least
          7 of these 9 conditions.
        </div>
      </section>

      <section className="stats">
        <div className="stat">
          <span>Shortlisted</span>
          <strong>{stocks.length}</strong>
        </div>
        <div className="stat">
          <span>9 / 9</span>
          <strong>{stats.nine}</strong>
        </div>
        <div className="stat">
          <span>8 / 9</span>
          <strong>{stats.eight}</strong>
        </div>
        <div className="stat">
          <span>7 / 9</span>
          <strong>{stats.seven}</strong>
        </div>
        <div className="stat">
          <span>Average RS</span>
          <strong>{format(stats.avgRS, 1)}</strong>
        </div>
      </section>

      <main className="table-card">
        <div className="table-header">
          <div>
            <h2>Shortlisted stocks</h2>
            <span>{timeframe === "daily" ? "Daily candles" : "4-hour candles"}</span>
          </div>
        </div>

        {loading ? (
          <div className="empty">Loading scanner results...</div>
        ) : visibleStocks.length === 0 ? (
          <div className="empty">
            No stocks match the current filters. Run the scanner first.
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Score</th>
                  <th>RS</th>
                  <th>Price</th>
                  <th>MA50</th>
                  <th>MA150</th>
                  <th>MA200</th>
                  <th>200MA slope</th>
                  <th>52W low</th>
                  <th>52W high</th>
                  <th>Checklist</th>
                  <th>Chart</th>
                </tr>
              </thead>
              <tbody>
                {visibleStocks.map((stock) => (
                  <tr key={stock.Symbol}>
                    <td>
                      <div className="stock-name">
                        <button className="symbol" onClick={() => setSelected(stock)}>
                          {stock.Symbol}
                        </button>

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
                      <span className={`score score-${stock.Score}`}>
                        {stock.Score}/9
                      </span>
                    </td>
                    <td className="rs">{format(stock["RS Rating"], 1)}</td>
                    <td>₹{format(stock.Price)}</td>
                    <td>₹{format(stock.MA50)}</td>
                    <td>₹{format(stock.MA150)}</td>
                    <td>₹{format(stock.MA200)}</td>
                    <td>{format(stock["MA200 slope %"])}%</td>
                    <td>+{format(stock["% Above 52W Low"], 1)}%</td>
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
                <div className="eyebrow">MINERVINI CHECKLIST</div>
                <h2>{selected.Symbol}</h2>
              </div>
              <button className="close" onClick={() => setSelected(null)}>×</button>
            </div>

            <div className="detail-grid">
              <div><span>Price</span><strong>₹{format(selected.Price)}</strong></div>
              <div><span>RS Rating</span><strong>{format(selected["RS Rating"], 1)}</strong></div>
              <div><span>Score</span><strong>{selected.Score}/9</strong></div>
              <div>
                <span>MA50</span>
                <strong>₹{format(selected.MA50)}</strong>
              </div>

              <div>
                <span>MA150</span>
                <strong>₹{format(selected.MA150)}</strong>
              </div>

              <div>
                <span>MA200</span>
                <strong>₹{format(selected.MA200)}</strong>
              </div>

              <div>
                <span>200MA slope</span>
                <strong>{format(selected["MA200 slope %"])}%</strong>
              </div>

              <div>
                <span>Above 52W low</span>
                <strong>+{format(selected["% Above 52W Low"], 1)}%</strong>
              </div>

              <div>
                <span>Below 52W high</span>
                <strong>-{format(selected["% Below 52W High"], 1)}%</strong>
              </div>
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
