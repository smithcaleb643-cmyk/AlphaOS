const API = "http://127.0.0.1:8000";

export default function LiveWalletCard({ liveWallet }) {
  return (
    <section className="brain-accounting-card">
      <div className="section-title">
        <span></span>
        <h2>🔗 Live Wallet</h2>
      </div>

      <div className="brain-grid compact">
        <div className="brain-card">
          <span>Status</span>
          <strong>{liveWallet?.connected ? "🟢 Connected" : "🔴 Offline"}</strong>
        </div>

        <div className="brain-card">
          <span>SOL Balance</span>
          <strong>{liveWallet?.sol_balance ?? 0}</strong>
        </div>

        <div className="brain-card">
          <span>Token Count</span>
          <strong>{liveWallet?.token_count ?? 0}</strong>
        </div>

        <div className="brain-card">
          <span>Mode</span>
          <strong>Read Only</strong>
        </div>
      </div>

      <div className="alpha-thought-box">
        <span>Wallet Address</span>
        <p style={{ wordBreak: "break-all", fontFamily: "monospace" }}>
          {liveWallet?.wallet_address || "No wallet connected"}
        </p>
      </div>
    </section>
  );
}