import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function LiveTraderPanel({ liveWallet }) {
  const [tokenAddress, setTokenAddress] = useState("");
  const [solAmount, setSolAmount] = useState("0.01");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function testDecision() {
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API}/live/decision/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token_address: tokenAddress,
          sol_amount: Number(solAmount),
          score: 90,
          probability: 80,
          risk_score: 20,
          coin_name: "Manual Live Test",
        }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ ok: false, error: String(error) });
    }

    setLoading(false);
  }

  async function executeBuy() {
    if (!confirm("This can send a REAL live transaction. Continue?")) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API}/live/execute/buy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token_address: tokenAddress,
          sol_amount: Number(solAmount),
          slippage_bps: 100,
        }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ ok: false, error: String(error) });
    }

    setLoading(false);
  }

  return (
    <section className="brain-accounting-card">
      <div className="section-title">
        <span></span>
        <h2>🔴 Live Trader</h2>
      </div>

      <div className="brain-grid compact">
        <div className="brain-card">
          <span>Wallet</span>
          <strong>{liveWallet?.connected ? "Connected" : "Offline"}</strong>
        </div>

        <div className="brain-card">
          <span>SOL Balance</span>
          <strong>{liveWallet?.sol_balance ?? 0}</strong>
        </div>

        <div className="brain-card">
          <span>Mode</span>
          <strong>Live Test</strong>
        </div>

        <div className="brain-card">
          <span>Max Test Buy</span>
          <strong>0.01 SOL</strong>
        </div>
      </div>

      <div style={{ display: "grid", gap: "10px", marginTop: "14px" }}>
        <input
          placeholder="Token mint address"
          value={tokenAddress}
          onChange={(e) => setTokenAddress(e.target.value)}
          style={{
            padding: "12px",
            borderRadius: "12px",
            background: "#050816",
            color: "white",
            border: "1px solid rgba(255,255,255,0.18)",
          }}
        />

        <input
          placeholder="SOL amount"
          value={solAmount}
          onChange={(e) => setSolAmount(e.target.value)}
          style={{
            padding: "12px",
            borderRadius: "12px",
            background: "#050816",
            color: "white",
            border: "1px solid rgba(255,255,255,0.18)",
          }}
        />

        <div className="engine-buttons">
          <button onClick={testDecision} disabled={loading || !tokenAddress}>
            🧠 Test Decision
          </button>

          <button className="red-btn" onClick={executeBuy} disabled={loading || !tokenAddress}>
            ⚡ Execute Live Buy
          </button>
        </div>
      </div>

      {result && (
        <div className="alpha-thought-box" style={{ marginTop: "14px" }}>
          <span>Live Result</span>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "12px" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}