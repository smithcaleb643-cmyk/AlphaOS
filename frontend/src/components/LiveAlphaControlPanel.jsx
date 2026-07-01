import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function LiveAlphaControlPanel({ liveAlpha, onRefresh }) {
  const [loading, setLoading] = useState(false);

  async function updateSettings(payload) {
    setLoading(true);

    await fetch(`${API}/live/alpha/settings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    await onRefresh?.();
    setLoading(false);
  }

  async function startLiveAlpha() {
    setLoading(true);
    await fetch(`${API}/live/alpha/start`, { method: "POST" });
    await onRefresh?.();
    setLoading(false);
  }

  async function stopLiveAlpha() {
    setLoading(true);
    await fetch(`${API}/live/alpha/stop`, { method: "POST" });
    await onRefresh?.();
    setLoading(false);
  }

  const executionMode = liveAlpha?.execution_mode || "MOCK";
  const autoBuyEnabled = !!liveAlpha?.auto_buy_enabled;

  return (
    <section className="brain-accounting-card">
      <div className="section-title">
        <span></span>
        <h2>🟢 Live Alpha Control</h2>
      </div>

      <div className="brain-grid compact">
        <div className="brain-card">
          <span>Status</span>
          <strong>{liveAlpha?.running ? "RUNNING" : "STOPPED"}</strong>
        </div>

        <div className="brain-card">
          <span>Execution Mode</span>
          <strong>{executionMode}</strong>
        </div>

        <div className="brain-card">
          <span>Auto Buy</span>
          <strong>{autoBuyEnabled ? "ON" : "OFF"}</strong>
        </div>

        <div className="brain-card">
          <span>Trade Size</span>
          <strong>${liveAlpha?.trade_size_usd ?? 1}</strong>
        </div>

        <div className="brain-card">
          <span>Max Positions</span>
          <strong>{liveAlpha?.max_open_positions ?? 1}</strong>
        </div>

        <div className="brain-card">
          <span>Daily Loss</span>
          <strong>${liveAlpha?.max_daily_loss_usd ?? 2}</strong>
        </div>
      </div>

      <div className="engine-buttons" style={{ marginTop: "14px" }}>
        <button
          disabled={loading || executionMode === "LIVE"}
          onClick={() => updateSettings({ execution_mode: "LIVE" })}
        >
          🔥 LIVE Mode
        </button>

        <button
          disabled={loading || executionMode === "MOCK"}
          onClick={() => updateSettings({ execution_mode: "MOCK" })}
        >
          🧪 MOCK Mode
        </button>

        <button
          disabled={loading || autoBuyEnabled}
          onClick={() => updateSettings({ auto_buy_enabled: true })}
        >
          ✅ Auto Buy ON
        </button>

        <button
          disabled={loading || !autoBuyEnabled}
          onClick={() => updateSettings({ auto_buy_enabled: false })}
        >
          ⛔ Auto Buy OFF
        </button>
      </div>

      <div className="alpha-thought-box" style={{ marginTop: "14px" }}>
        <span>Last Action</span>
        <p>{liveAlpha?.last_action || "Idle"}</p>
      </div>

      <div className="engine-buttons" style={{ marginTop: "14px" }}>
        <button onClick={startLiveAlpha} disabled={loading || liveAlpha?.running}>
          🟢 Start Live Alpha
        </button>

        <button
          className="red-btn"
          onClick={stopLiveAlpha}
          disabled={loading || !liveAlpha?.running}
        >
          🛑 Stop Live Alpha
        </button>
      </div>
    </section>
  );
}