import { useEffect, useState } from "react";
import AlphaLiveChart from "./AlphaLiveChart";
import "./App.css";

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
  return `$${Number(value).toLocaleString()}`;
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

  async function loadMemory() {
    setIsLoadingMemory(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/memory");
      const data = await response.json();
      setMemory(data.scans || []);
    } catch (error) {
      console.error(error);
      alert("Could not load Alpha memory.");
    }

    setIsLoadingMemory(false);
  }

  async function runScan() {
  setIsScanning(true);

  try {
    const response = await fetch("http://127.0.0.1:8000/scan");
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
  } catch (error) {
    console.error(error);
    alert("Alpha backend is not responding.");
  }

  setIsScanning(false);
}

  useEffect(() => {
    loadMemory();
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
      return (
        <PlaceholderPage
          title="Trader"
          subtitle="Paper trading and trade management page."
          items={[
            { title: "Open Positions", text: "Entry, size, value, P&L, status." },
            { title: "Execute Plan", text: "Alpha can simulate trades before live trading." },
            { title: "Review", text: "Alpha explains whether to hold, exit, or tighten stop." },
          ]}
        />
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
      return (
        <PlaceholderPage
          title="Alpha Brain"
          subtitle="Alpha's reasoning, memory, and learning center."
          items={[
            { title: "Memory", text: "Alpha remembers every scan and trade." },
            { title: "Learning Engine", text: "Finds which patterns win or rug." },
            { title: "Reasoning", text: "Explains why Alpha likes or rejects a coin." },
          ]}
        />
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