import { useEffect, useState } from "react";
import LiveTradeJournalPanel from "./components/LiveTradeJournalPanel";
import AlphaLiveChart from "./AlphaLiveChart";
import LivePortfolioPanel from "./components/LivePortfolioPanel";
import LiveAlphaControlPanel from "./components/LiveAlphaControlPanel";
import LiveWalletCard from "./components/LiveWalletCard";
import "./App.css";

const API = "http://127.0.0.1:8000";

const defaultWatchlist = [
  {
    coin_name: "three.ws",
    score: 85,
    action: "BUY",
    probability: 100,
    risk_score: 10,
    status: "watching",
    liquidity: 2310000,
    volume: 12450000,
    market_cap: 7000000,
    holders: 18742,
    age_minutes: 33120,
    price_change: 18.24,
    reason: "Strong liquidity, strong volume, healthy momentum.",
  },
  {
    coin_name: "BONKAI",
    score: 50,
    action: "WATCH",
    probability: 65,
    risk_score: 35,
    status: "watching",
    liquidity: 32000,
    volume: 81000,
    market_cap: 160000,
    holders: 245,
    age_minutes: 28,
    price_change: 24,
    reason: "Early coin with mixed signals.",
  },
  {
    coin_name: "RUGDOGE",
    score: 0,
    action: "REJECT",
    probability: 0,
    risk_score: 75,
    status: "rejected",
    liquidity: 9000,
    volume: 14000,
    market_cap: 60000,
    holders: 41,
    age_minutes: 4,
    price_change: 170,
    reason: "High risk structure.",
  },
];

function formatMoney(value) {
  if (value === undefined || value === null) return "—";
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatSmall(value) {
  if (value === undefined || value === null) return "—";
  return `$${Number(value).toFixed(8)}`;
}

function formatPercent(value) {
  if (value === undefined || value === null) return "0%";
  return `${Number(value).toFixed(1)}%`;
}

function getPnlClass(value) {
  return Number(value || 0) >= 0 ? "green" : "red";
}

function PlaceholderPage({ title, subtitle, items }) {
  return (
    <main className="single-page">
      <section className="panel placeholder-page">
        <h2>{title}</h2>
        <p>{subtitle}</p>

        <div className="placeholder-grid">
          {items.map((item) => (
            <div className="placeholder-card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function App() {
  const [currentPage, setCurrentPage] = useState("Dashboard");
const [coins, setCoins] = useState(defaultWatchlist);
const [selectedCoin, setSelectedCoin] = useState(defaultWatchlist[0]);
const [memory, setMemory] = useState([]);
const [memorySearch, setMemorySearch] = useState("");
const [memoryFilter, setMemoryFilter] = useState("ALL");
const [sortByScore, setSortByScore] = useState(true);
const [autoRefresh, setAutoRefresh] = useState(false);
const [showDetails, setShowDetails] = useState(false);
const [isScanning, setIsScanning] = useState(false);
const [isLoadingMemory, setIsLoadingMemory] = useState(false);

const [paperPerformance, setPaperPerformance] = useState(null);
const [paperState, setPaperState] = useState(null);
const [learningState, setLearningState] = useState(null);
const [engineState, setEngineState] = useState(null);
const [systemHealth, setSystemHealth] = useState(null);

const [liveWallet, setLiveWallet] = useState(null);

const [livePortfolio, setLivePortfolio] = useState(null);

const [liveAlpha, setLiveAlpha] = useState(null);

const [liveJournal, setLiveJournal] = useState({
  count: 0,
  trades: [],
});

  async function loadMemory() {
    setIsLoadingMemory(true);

    try {
      const response = await fetch(`${API}/memory`);
      if (!response.ok) {
        setMemory([]);
        return;
      }

      const data = await response.json();
      setMemory(data.scans || []);
    } catch (error) {
      console.error("Memory load failed:", error);
      setMemory([]);
    }

    setIsLoadingMemory(false);
  }

  async function loadPaperTrader() {
  try {
    const perf = await fetch(`${API}/paper/performance`).then((r) => r.json());
    const state = await fetch(`${API}/paper/state`).then((r) => r.json());
    const learning = await fetch(`${API}/paper/learning`).then((r) => r.json());
    const engine = await fetch(`${API}/engine/state`).then((r) => r.json());

    setPaperPerformance(perf);
    setPaperState(state);
    setLearningState(learning);
    setEngineState(engine);
  } catch (error) {
    console.error("Paper trader load failed:", error);
  }
}

async function loadSystemHealth() {
  try {
    const response = await fetch(`${API}/system/health`);
    const data = await response.json();
    setSystemHealth(data);
  } catch (error) {
    console.error("System health load failed:", error);
  }
}

async function loadLiveWallet() {
  try {
    const response = await fetch(`${API}/live/wallet/status`);
    const data = await response.json();
    setLiveWallet(data);
  } catch (error) {
    console.error("Live wallet load failed:", error);
  }
}

async function loadLiveTradeJournal() {
  try {
    const response = await fetch(`${API}/live/trade-journal`);
    const data = await response.json();
    setLiveJournal(data);
  } catch (error) {
    console.error("Live trade journal load failed:", error);
  }
}

async function loadLivePortfolio() {
  try {
    const response = await fetch(`${API}/live/portfolio`);
    const data = await response.json();
    setLivePortfolio(data);
  } catch (error) {
    console.error("Live portfolio load failed:", error);
  }
}

async function loadLiveAlphaState() {
  try {
    const response = await fetch(`${API}/live/alpha/state`);
    const data = await response.json();
    setLiveAlpha(data);
  } catch (error) {
    console.error("Live Alpha state load failed:", error);
  }
}

async function startAlphaEngine() {
  try {
    await fetch(`${API}/engine/start`, { method: "POST" });

    await loadPaperTrader();
    await loadLiveWallet();
    await loadLivePortfolio();
    await loadLiveAlphaState();
    await loadLiveTradeJournal();

  } catch (error) {
    console.error("Engine start failed:", error);
    alert("Could not start Alpha Engine.");
  }
}

async function stopAlphaEngine() {
  try {
    await fetch(`${API}/engine/stop`, { method: "POST" });

    await loadPaperTrader();
    await loadLiveWallet();
    await loadLivePortfolio();
    await loadLiveAlphaState();
    await loadLiveTradeJournal();

  } catch (error) {
    console.error("Engine stop failed:", error);
    alert("Could not stop Alpha Engine.");
  }
}

async function reviewTrade(tradeId) {
  try {
    const response = await fetch(`${API}/paper/trade/${tradeId}/review`, {
      method: "POST",
    });

    const data = await response.json();
    console.log("REVIEW RESPONSE:", data);

    await loadPaperTrader();
  } catch (error) {
    console.error("Review failed:", error);
    alert("Review failed. Check backend terminal.");
  }
}

async function sellTrade(tradeId) {
  try {
    const response = await fetch(`${API}/paper/trade/${tradeId}/sell`, {
      method: "POST",
    });

    const data = await response.json();
    console.log("SELL RESPONSE:", data);

    await loadPaperTrader();
  } catch (error) {
    console.error("Sell failed:", error);
    alert("Sell failed. Check backend terminal.");
  }
}

async function runScan() {
  setIsScanning(true);

  try {
    const response = await fetch(`${API}/scan`);
    const data = await response.json();

    console.log("LIVE SCAN:", data);

    if (!data.results || data.results.length === 0) {
      alert("Alpha scanned but found no live coins yet.");
      setIsScanning(false);
      return;
    }

    setCoins(data.results);
    setSelectedCoin(data.results[0]);

    await loadMemory();
    await loadPaperTrader();
    await loadLiveWallet();
    await loadLivePortfolio();
    await loadLiveAlphaState();
    await loadLiveTradeJournal();

  } catch (error) {
    console.error(error);
    alert("Alpha backend is not responding.");
  }

  setIsScanning(false);
}

  useEffect(() => {
  loadMemory();
  loadPaperTrader();
  loadSystemHealth();
  loadLiveWallet();
  loadLivePortfolio();
  loadLiveAlphaState();
  loadLiveTradeJournal();

  const timer = setInterval(() => {
    loadPaperTrader();
    loadSystemHealth();
  }, 1000);

  const walletTimer = setInterval(() => {
    loadLiveWallet();
  }, 10000);

  const journalTimer = setInterval(() => {
    loadLiveTradeJournal();
    loadLivePortfolio();
    loadLiveAlphaState();
  }, 3000);

  return () => {
    clearInterval(timer);
    clearInterval(walletTimer);
    clearInterval(journalTimer);
  };
}, []);

useEffect(() => {
  if (!autoRefresh) return;

  const timer = setInterval(() => {
    runScan();
  }, 15000);

  return () => clearInterval(timer);
}, [autoRefresh]);

  const latestMemoryByCoin = Object.values(
    memory.reduce((acc, scan) => {
      if (!acc[scan.coin_name]) {
        acc[scan.coin_name] = scan;
      }
      return acc;
    }, {})
  );

  const filteredMemory = latestMemoryByCoin
    .filter((scan) => {
      const matchesSearch = scan.coin_name
        ?.toLowerCase()
        .includes(memorySearch.toLowerCase());

      const matchesFilter =
        memoryFilter === "ALL" || scan.action === memoryFilter;

      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      if (!sortByScore) return 0;
      return (b.score ?? 0) - (a.score ?? 0);
    });

  const actionClass = selectedCoin.action?.toLowerCase() || "watch";

  const pages = [
    "Dashboard",
    "Scanner",
    "Charts",
    "Trader",
    "Portfolio",
    "Alpha Brain",
    "Settings",
  ];

  function renderPage() {
    if (currentPage === "Scanner") {
      return (
        <PlaceholderPage
          title="Scanner"
          subtitle="Dedicated live scanner page. This will become the main place for new Solana launches."
          items={[
            { title: "Live Launches", text: "Connected to Alpha's /scan endpoint." },
            { title: "Filters", text: "BUY, WATCH, REJECT, liquidity, volume, age." },
            { title: "Auto Mode", text: "Auto-refresh already works from the dashboard." },
          ]}
        />
      );
    }

    if (currentPage === "Charts") {
      return (
        <main className="single-page">
          <section className="panel placeholder-page">
            <h2>Live Charts</h2>
            <p>Real DexScreener market chart embedded inside Alpha OS.</p>
            <AlphaLiveChart />
          </section>
        </main>
      );
    }

    if (currentPage === "Trader") {
      const perf = paperPerformance || {};
      const state = paperState || {};
      const learning = learningState || {};
      const engine = engineState || {};
      const openTrades = state.open_trades || [];
      const closedTrades = state.closed_trades || [];

      function tradeName(trade) {
        return trade?.symbol || trade?.coin_name || "UNKNOWN";
      }

      function tradeSubtitle(trade) {
        return trade?.coin_name || "Alpha paper trade";
      }

      function tradeValue(trade) {
        const entry = Number(trade?.entry_price || 0);
        const qty = Number(trade?.quantity || 0);
        const current = Number(trade?.current_price || entry);
        return qty * current;
      }

      function tradePnlClass(trade) {
        return Number(trade?.pnl_usd || 0) >= 0 ? "green" : "red";
      }

      function alphaReason(trade) {
        return `Alpha bought because Edge ${trade?.score ?? 0}, Probability ${
          trade?.probability ?? 0
        }%, Risk ${trade?.risk_score ?? 0}. ${trade?.reason || ""}`;
      }

      return (
        <main className="alpha-trader-mobile">
          <section className="trader-top-card">
            <div>
              <h1>Alpha Trader</h1>
              <p>AI paper trading command center</p>
            </div>

            <div className="engine-pill">
              <span className={engine.running ? "green" : "red"}>
                ● {engine.running ? "RUNNING" : "STOPPED"}
              </span>
            </div>
          </section>

          <section className="trader-performance-card">
            <div className="section-title">
              <span></span>
              <h2>Performance</h2>
            </div>

            <div className="performance-grid">
              <div>
                <span>Win rate</span>
                <strong>{perf.win_rate ?? 0}%</strong>
              </div>
              <div>
                <span>Closed P&L</span>
                <strong className={getPnlClass(perf.total_pnl)}>
                  {formatMoney(perf.total_pnl ?? 0)}
                </strong>
              </div>
              <div>
                <span>Open positions</span>
                <strong>{perf.open_trades ?? openTrades.length}</strong>
              </div>
              <div>
                <span>Closed trades</span>
                <strong>{perf.closed_trades ?? closedTrades.length}</strong>
              </div>
            </div>

            <div className="engine-buttons">
              <button onClick={startAlphaEngine}>Start Engine</button>
              <button onClick={stopAlphaEngine}>Stop Engine</button>
            </div>
          </section>

          <section className="trader-copilot-card">
            <div className="section-title">
              <span></span>
              <h2>Alpha Copilot Status</h2>
            </div>

            <p>
              Alpha scanned {engine.last_scan_count ?? 0} coins. New trades this cycle:{" "}
              {engine.last_trades_created ?? 0}.
            </p>

            <div className="copilot-mini-grid">
              <div>
                <span>Cash left</span>
                <strong>{formatMoney(perf.cash ?? 10000)}</strong>
              </div>
              <div>
                <span>Equity</span>
                <strong>{formatMoney(perf.equity ?? 10000)}</strong>
              </div>
              <div>
                <span>Cycles</span>
                <strong>{engine.cycles ?? 0}</strong>
              </div>
              <div>
                <span>Learned</span>
                <strong>{learning.total_trades ?? 0}</strong>
              </div>
            </div>
          </section>

          <section className="section-title floating-title">
            <span></span>
            <h2>Open Positions</h2>
          </section>

          {openTrades.length === 0 ? (
            <section className="empty-trader-card">
              <h2>No open trades</h2>
              <p>Start Alpha Engine and let it scan for opportunities.</p>
            </section>
          ) : (
            <section className="position-stack">
              {openTrades.map((trade) => (
                <article className="position-card" key={trade.id}>
                  <div className="position-header">
                    <div className="position-left">
                      <div className="trade-avatar">🤖</div>
                      <div>
                        <h2>{tradeName(trade)}</h2>
                        <p>{tradeSubtitle(trade)}</p>
                        <div className="pill-row">
                          <span>Edge {trade.score ?? 0}</span>
                          <span>Prob {trade.probability ?? 0}%</span>
                        </div>
                      </div>
                    </div>

                    <div className="position-pnl">
                      <span>P&L</span>
                      <strong className={tradePnlClass(trade)}>
                        {formatPercent(trade.pnl_percent)}
                      </strong>
                      <p className={tradePnlClass(trade)}>
                        {formatMoney(trade.pnl_usd ?? 0)}
                      </p>
                    </div>
                  </div>

                  <div className="trade-stat-grid">
                    <div>
                      <span>Invested</span>
                      <strong>{formatMoney(trade.size_usd ?? 0)}</strong>
                    </div>
                    <div>
                      <span>Value</span>
                      <strong>{formatMoney(tradeValue(trade))}</strong>
                    </div>
                    <div>
                      <span>Size</span>
                      <strong>{trade.quantity ? "Active" : "—"}</strong>
                    </div>
                  </div>

                  <div className="reason-box">{alphaReason(trade)}</div>

                  <div className="monitoring-box">
                    <h2>🟡 Alpha still monitoring</h2>
                    <p>
                      Alpha is watching the trade. It will close automatically if TP or SL is reached.
                    </p>

                    <div className="levels-grid">
                      <div>
                        <span>Entry</span>
                        <strong>{formatSmall(trade.entry_price)}</strong>
                      </div>
                      <div>
                        <span>Current</span>
                        <strong>{formatSmall(trade.current_price)}</strong>
                      </div>
                      <div>
                        <span>Stop</span>
                        <strong className="red">{formatSmall(trade.stop_loss)}</strong>
                      </div>
                      <div>
                        <span>Take Profit</span>
                        <strong className="green">{formatSmall(trade.take_profit)}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="caution-box">
                    <h2>🧠 Alpha Review</h2>
                    <p>{trade.review || "Click Review and Alpha will rethink this trade."}</p>

                    <div className="review-grid">
                      <div>
                        <span>Recommendation</span>
                        <strong>{trade.recommendation || "WAIT"}</strong>
                      </div>
                      <div>
                        <span>Prob</span>
                        <strong>{trade.probability ?? 0}%</strong>
                      </div>
                      <div>
                        <span>Risk</span>
                        <strong>{trade.risk_score ?? 0}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="trade-action-grid">
                    <button onClick={loadPaperTrader}>↻ Update</button>

                    <button
                      className="purple-btn"
                      onClick={() => reviewTrade(trade.id)}
                    >
                      🧠 Review
                    </button>

                    <button
                      className="green-btn"
                      onClick={() => {
                        alert("Execute Plan is next. Alpha will move stops, trail winners, and take partial profits.");
                      }}
                    >
                      ⚡ Execute Plan
                    </button>

                    <button
                      className="red-btn"
                      onClick={() => sellTrade(trade.id)}
                    >
                      Sell
                    </button>
                  </div>
                </article>
              ))}
            </section>
          )}

          <section className="section-title floating-title">
            <span></span>
            <h2>Recent Trades</h2>
          </section>

          <section className="recent-trades-card">
            {closedTrades.length === 0 ? (
              <p>No closed trades yet.</p>
            ) : (
              closedTrades.slice(-8).reverse().map((trade) => (
                <div className="recent-trade-row" key={trade.id}>
                  <div className="check-icon">✓</div>

                  <div>
                    <strong>{tradeName(trade)}</strong>
                    <span>{trade.closed_at || trade.opened_at}</span>
                  </div>

                  <div className="recent-pnl">
                    <strong className={tradePnlClass(trade)}>
                      {formatPercent(trade.pnl_percent)}
                    </strong>
                    <span className={tradePnlClass(trade)}>
                      {formatMoney(trade.pnl_usd ?? 0)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </section>
        </main>
      );
    }

    if (currentPage === "Portfolio") {
      return (
        <PlaceholderPage
          title="Portfolio"
          subtitle="Portfolio tracking and performance dashboard."
          items={[
            { title: "Equity", text: "Track account balance and open P&L." },
            { title: "Closed Trades", text: "Win rate, average return, worst loss." },
            { title: "Risk", text: "Exposure, cash, position sizing, drawdown." },
          ]}
        />
      );
    }

    if (currentPage === "Alpha Brain") {
  const health = systemHealth || {};
  const accounting = health.accounting || {};
  const warnings = health.warnings || [];
  const safe = health.status === "SAFE";
  const brain = health.brain || {};
const learning = health.learning || {};

  return (
    <main className="alpha-brain-page">
      <section className={`brain-hero ${safe ? "safe" : "warning"}`}>
        <div>
          <p className="eyebrow">Alpha Brain</p>
          <h1>{safe ? "🟢 Alpha Safe" : "🟡 Alpha Warning"}</h1>
          <p>
            {safe
              ? "All core systems are balanced and reporting normally."
              : "Alpha found warnings that need review."}
          </p>
        </div>

        <div className="brain-score-orb">
          <span>{safe ? "SAFE" : "CHECK"}</span>
        </div>
      </section>

      <section className="brain-grid">
        <div className="brain-card">
          <span>Backend</span>
          <strong>{health.backend_online ? "Online" : "Offline"}</strong>
          <p>Core API status</p>
        </div>

        <div className="brain-card">
          <span>Paper Memory</span>
          <strong>{health.paper_state_file?.exists ? "Saved" : "Missing"}</strong>
          <p>Trades survive restart</p>
        </div>

        <div className="brain-card">
          <span>Learning Memory</span>
          <strong>{health.saved_learning?.has_learning ? "Saved" : "Missing"}</strong>
          <p>{health.saved_learning?.saved_at || "No save yet"}</p>
        </div>

        <div className="brain-card">
          <span>Price Audit</span>
          <strong>{health.price_audit_file?.exists ? "Active" : "Missing"}</strong>
          <p>
            Last update:{" "}
            {health.last_price_update_age_seconds == null
              ? "none"
              : `${health.last_price_update_age_seconds}s ago`}
          </p>
        </div>
      </section>

      <LiveAlphaControlPanel
        liveAlpha={liveAlpha}
        onRefresh={loadLiveAlphaState}
      />

      <LiveWalletCard liveWallet={liveWallet} />

      <LivePortfolioPanel livePortfolio={livePortfolio} />

      <LiveTradeJournalPanel liveJournal={liveJournal} />

      <section className="brain-accounting-card">
        <div className="section-title">
          <span></span>
          <h2>Accounting Audit</h2>
        </div>

        <div className="accounting-formula">
          <strong>{formatMoney(accounting.cash || 0)}</strong>
          <span>+</span>
          <strong>{formatMoney(accounting.open_value || 0)}</strong>
          <span>=</span>
          <strong>{formatMoney(accounting.equity || 0)}</strong>
        </div>

        <p>Cash + Open Position Value = Total Equity</p>

        <div className="brain-grid compact">
          <div className="brain-card">
            <span>Total P&L</span>
            <strong className={getPnlClass(accounting.total_pnl)}>
              {formatMoney(accounting.total_pnl || 0)}
            </strong>
          </div>

          <div className="brain-card">
            <span>Closed P&L</span>
            <strong className={getPnlClass(accounting.closed_pnl)}>
              {formatMoney(accounting.closed_pnl || 0)}
            </strong>
          </div>

          <div className="brain-card">
            <span>Open Trades</span>
            <strong>{accounting.open_trades || 0}</strong>
          </div>

          <div className="brain-card">
            <span>Closed Trades</span>
            <strong>{accounting.closed_trades || 0}</strong>
          </div>
        </div>
      </section>
<section className="brain-accounting-card">
  <div className="section-title">
    <span></span>
    <h2>Alpha Mind</h2>
  </div>

  <div className="brain-grid compact">
    <div className="brain-card">
      <span>Mood</span>
      <strong>{brain.mood || "Loading"}</strong>
    </div>

    <div className="brain-card">
      <span>Confidence</span>
      <strong>{brain.confidence ?? 0}%</strong>
    </div>

    <div className="brain-card">
      <span>Strategy</span>
      <strong>{brain.strategy_mode || "Unknown"}</strong>
    </div>

    <div className="brain-card">
      <span>Wallet AI</span>
      <strong>{brain.wallet_ai || "STANDBY"}</strong>
    </div>
  </div>

  <div className="alpha-thought-box">
    <span>Alpha Thought</span>
    <p>{brain.thought || "Waiting for health data..."}</p>
  </div>

  <div className="learning-bars">
    {(brain.learning_bars || []).map((bar) => (
      <div className="learning-bar-row" key={bar.name}>
        <div>
          <span>{bar.name}</span>
          <strong>{bar.value}%</strong>
        </div>
        <div className="learning-track">
          <div
            className="learning-fill"
            style={{ width: `${bar.value}%` }}
          ></div>
        </div>
      </div>
    ))}
  </div>

  <div className="brain-grid compact">
    <div className="brain-card">
      <span>Learned Trades</span>
      <strong>{learning.total_trades || 0}</strong>
    </div>

    <div className="brain-card">
      <span>Win Rate</span>
      <strong>{learning.win_rate || 0}%</strong>
    </div>

    <div className="brain-card">
      <span>Engine Cycles</span>
      <strong>{brain.cycles || 0}</strong>
    </div>

    <div className="brain-card">
      <span>Last Scan</span>
      <strong>{brain.last_scan_count || 0} coins</strong>
    </div>
  </div>
</section>
      <section className="brain-accounting-card">
        <div className="section-title">
          <span></span>
          <h2>System Warnings</h2>
        </div>

        {warnings.length === 0 ? (
          <div className="warning-good">✅ No warnings. Alpha systems are healthy.</div>
        ) : (
          <div className="warning-list">
            {warnings.map((warning, index) => (
              <div className="warning-item" key={index}>
                ⚠️ {warning}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

    if (currentPage === "Settings") {
      return (
        <PlaceholderPage
          title="Settings"
          subtitle="Control Alpha OS behavior."
          items={[
            { title: "Scanner Settings", text: "Liquidity, volume, age, risk limits." },
            { title: "Risk Settings", text: "Max position size, stop loss, paper trading." },
            { title: "API Settings", text: "DexScreener, Helius, Birdeye, wallet sources." },
          ]}
        />
      );
    }

    return (
      <main className="dashboard-grid">
        <aside className="left-column">
          <section className="panel watchlist-panel">
            <div className="panel-heading">
              <h2>LIVE SCANNER</h2>
              <button onClick={runScan}>{isScanning ? "..." : "Scan"}</button>
            </div>

            {coins.map((coin) => (
              <div
                className={`watch-row ${
                  selectedCoin.coin_name === coin.coin_name ? "selected-row" : ""
                }`}
                key={coin.coin_name}
                onClick={() => setSelectedCoin(coin)}
              >
                <div className={`coin-icon ${coin.action?.toLowerCase()}`}>
                  🤖
                </div>
                <div>
                  <strong>{coin.coin_name}</strong>
                  <span>{coin.action}</span>
                </div>
                <div className="watch-price">
                  <strong>{coin.score}</strong>
                  <span className={coin.action === "REJECT" ? "red" : "green"}>
                    {coin.probability ?? 0}%
                  </span>
                </div>
              </div>
            ))}

            <button className="add-coin">+ Add Coin</button>
          </section>

          <section className="panel sentiment-panel">
            <h2>MARKET SENTIMENT</h2>
            <div className="gauge">
              <div className="gauge-number">72</div>
              <span>Greed</span>
            </div>
            <p>Coming from 69 — scanner momentum improving.</p>
          </section>

          <section className="panel news-panel">
            <h2>AI NEWS FEED</h2>
            <p>2m ago • Alpha scan completed</p>
            <p>7m ago • Solana memecoin activity rising</p>
            <p>11m ago • Wallet radar waiting for live indexer</p>
          </section>
        </aside>

        <section className="center-column">
          <div className="coin-header panel">
            <div className="coin-title">
              <div className={`large-bot ${actionClass}`}>🤖</div>
              <div>
                <h2>{selectedCoin.coin_name}</h2>
                <p>{selectedCoin.status || "scanned"}</p>
              </div>
            </div>

            <div className="price-block">
              <h2>
                Score {selectedCoin.score} <span>{selectedCoin.action}</span>
              </h2>
            </div>

            <div className="coin-stats">
              <div>
                <span>Volume</span>
                <strong>{formatMoney(selectedCoin.volume)}</strong>
              </div>
              <div>
                <span>Liquidity</span>
                <strong>{formatMoney(selectedCoin.liquidity)}</strong>
              </div>
              <div>
                <span>Holders</span>
                <strong>{selectedCoin.holders ?? "—"}</strong>
              </div>
              <div>
                <span>Age</span>
                <strong>{selectedCoin.age_minutes ?? "—"}m</strong>
              </div>
            </div>

            <button className="trade-btn" onClick={() => setShowDetails(true)}>
              Details
            </button>
          </div>

          <section className="panel chart-panel">
            <div className="chart-toolbar">
              <span>1m</span>
              <span>5m</span>
              <span className="active">15m</span>
              <span>1h</span>
              <span>4h</span>
              <span>D</span>
              <span>DexScreener Live</span>
            </div>

            <AlphaLiveChart />
          </section>

          <section className="analysis-tabs">
            <button className="active">Alpha Analysis</button>
            <button>Trade History</button>
            <button>Order Book</button>
            <button>Holder Analysis</button>
            <button>Liquidity</button>
            <button>Risk Check</button>
          </section>

          <section className="bottom-panels">
            <div className="panel insight-panel">
              <h2>AI INSIGHT</h2>
              <h3>
                {selectedCoin.action === "BUY"
                  ? "Strong Opportunity"
                  : selectedCoin.action === "WATCH"
                  ? "Needs Confirmation"
                  : "High Risk"}
              </h3>
              <p>{selectedCoin.reason}</p>
              <ul>
                <li>✓ Score: {selectedCoin.score}</li>
                <li>✓ Probability: {selectedCoin.probability ?? 0}%</li>
                <li>✓ Risk Score: {selectedCoin.risk_score ?? 0}</li>
                <li>✓ Action: {selectedCoin.action}</li>
              </ul>
            </div>

            <div className="panel score-panel">
              <h2>ALPHA SCORE</h2>
              <div className="score-ring">
                {selectedCoin.score}
                <span>/100</span>
              </div>
              <p>{selectedCoin.action}</p>
              <div className="score-metrics">
                <div>
                  <strong>{selectedCoin.score}</strong>
                  <span>Edge</span>
                </div>
                <div>
                  <strong>{selectedCoin.probability ?? 0}%</strong>
                  <span>Prob</span>
                </div>
                <div>
                  <strong>{100 - (selectedCoin.risk_score ?? 0)}</strong>
                  <span>Safety</span>
                </div>
                <div>
                  <strong>2.40</strong>
                  <span>R:R</span>
                </div>
              </div>
            </div>

            <div className="panel levels-panel">
              <h2>KEY LEVELS</h2>
              <p>Entry <span className="green">Watch confirmation</span></p>
              <p>Stop Loss <span className="red">-8%</span></p>
              <p>TP1 <span className="green">+12%</span></p>
              <p>TP2 <span className="green">+24%</span></p>
              <p>TP3 <span className="green">+45%</span></p>
            </div>
          </section>

          <section className="panel positions-panel">
            <div className="panel-heading">
              <h2>ALPHA MEMORY</h2>
              <button onClick={loadMemory}>
                {isLoadingMemory ? "Loading..." : "Refresh"}
              </button>
            </div>

            <div className="memory-controls">
              <input
                placeholder="Search memory..."
                value={memorySearch}
                onChange={(event) => setMemorySearch(event.target.value)}
              />

              <select
                value={memoryFilter}
                onChange={(event) => setMemoryFilter(event.target.value)}
              >
                <option value="ALL">All Actions</option>
                <option value="BUY">BUY</option>
                <option value="WATCH">WATCH</option>
                <option value="REJECT">REJECT</option>
              </select>

              <button
                className="memory-toggle"
                onClick={() => setSortByScore(!sortByScore)}
              >
                {sortByScore ? "Sorted: Score" : "Sorted: Recent"}
              </button>

              <button
                className={autoRefresh ? "memory-toggle active-toggle" : "memory-toggle"}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                {autoRefresh ? "Auto ON" : "Auto OFF"}
              </button>

              <span>
                Showing {filteredMemory.length} latest coins from {memory.length} saved scans
              </span>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Coin</th>
                  <th>Score</th>
                  <th>Risk</th>
                  <th>Probability</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredMemory.map((scan) => (
                  <tr
                    key={scan.id}
                    className="clickable-row"
                    onClick={() => setSelectedCoin(scan)}
                    onDoubleClick={() => {
                      setSelectedCoin(scan);
                      setShowDetails(true);
                    }}
                  >
                    <td>{scan.coin_name}</td>
                    <td>{scan.score}</td>
                    <td>{scan.risk_score ?? 0}</td>
                    <td>{scan.probability ?? 0}%</td>
                    <td>{scan.status}</td>
                    <td className={scan.action === "REJECT" ? "red" : "green"}>
                      {scan.action}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </section>

        <aside className="right-column">
          <section className="panel portfolio-panel">
            <h2>PORTFOLIO OVERVIEW</h2>
            <p>Total Balance</p>
            <h3>$2,451.32</h3>
            <span className="green">+$145.64 (6.31%) 24h</span>
            <div className="mini-chart"></div>
            <div className="breakdown">
              <p>Open Positions <strong>$1,324.18</strong></p>
              <p>Cash <strong>$927.14</strong></p>
              <p>Realized P&L <strong>$200.56</strong></p>
            </div>
          </section>

          <section className="panel brain-panel">
            <h2>ALPHA BRAIN STATUS</h2>
            <p>◎ Backend API <span>Active</span></p>
            <p>◎ Scanner Engine <span>Active</span></p>
            <p>◎ Risk Engine <span>Active</span></p>
            <p>◎ Memory Engine <span>Active</span></p>
            <p>◎ Live Chart <span>Active</span></p>
            <strong>Frontend connected to Python</strong>
          </section>

          <section className="panel performance-panel">
            <h2>SELECTED COIN</h2>
            <p>Liquidity <strong>{formatMoney(selectedCoin.liquidity)}</strong></p>
            <p>Volume <strong>{formatMoney(selectedCoin.volume)}</strong></p>
            <p>Market Cap <strong>{formatMoney(selectedCoin.market_cap)}</strong></p>
            <p>Holders <strong>{selectedCoin.holders ?? "—"}</strong></p>
            <p>
              Price Change{" "}
              <strong className={selectedCoin.price_change > 0 ? "green" : "red"}>
                {selectedCoin.price_change ?? 0}%
              </strong>
            </p>
          </section>
        </aside>
      </main>
    );
  }

  return (
    <div className="alpha-app">
      <header className="top-nav">
        <div className="brand-block">
          <div className="alpha-mark">🤖</div>
          <div>
            <h1>ALPHA OS <span>v3.0</span></h1>
            <p>AI Crypto Copilot</p>
          </div>
        </div>

        <nav className="desktop-nav">
          {pages.map((page) => (
            <button
              key={page}
              className={currentPage === page ? "active" : ""}
              onClick={() => setCurrentPage(page)}
            >
              {page}
            </button>
          ))}
        </nav>

        <div className="user-block">
          <span className="online-dot">● AI Online</span>
          <strong>Caleb</strong>
          <div className="avatar">🤖</div>
        </div>
      </header>

      <div className="market-strip">
        <div>Market Mode <strong>Live</strong></div>
        <div>🟠 BTC <strong>$67,842.12</strong> <span className="green">+1.35%</span></div>
        <div>🔵 SOL <strong>$148.21</strong> <span className="green">+2.41%</span></div>
        <div>💎 TOTAL <strong>$2.58T</strong> <span className="green">+1.62%</span></div>
        <button onClick={runScan}>
          {isScanning ? "Scanning..." : "🤖 Run Alpha Scan"}
        </button>
      </div>

      {renderPage()}

      {showDetails && (
        <div className="modal-backdrop" onClick={() => setShowDetails(false)}>
          <div className="coin-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{selectedCoin.coin_name}</h2>
                <p>{selectedCoin.action} • {selectedCoin.status}</p>
              </div>
              <button onClick={() => setShowDetails(false)}>×</button>
            </div>

            <div className="modal-grid">
              <div><span>Score</span><strong>{selectedCoin.score}</strong></div>
              <div><span>Probability</span><strong>{selectedCoin.probability ?? 0}%</strong></div>
              <div><span>Risk</span><strong>{selectedCoin.risk_score ?? 0}</strong></div>
              <div><span>Liquidity</span><strong>{formatMoney(selectedCoin.liquidity)}</strong></div>
              <div><span>Volume</span><strong>{formatMoney(selectedCoin.volume)}</strong></div>
              <div><span>Market Cap</span><strong>{formatMoney(selectedCoin.market_cap)}</strong></div>
              <div><span>Holders</span><strong>{selectedCoin.holders ?? "—"}</strong></div>
              <div><span>Price Change</span><strong>{selectedCoin.price_change ?? 0}%</strong></div>
            </div>

            <div className="modal-reason">
              <h3>Alpha Reasoning</h3>
              <p>{selectedCoin.reason}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;