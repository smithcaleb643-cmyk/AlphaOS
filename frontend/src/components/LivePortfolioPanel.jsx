export default function LivePortfolioPanel({ livePortfolio }) {
  const portfolio = livePortfolio || {};
  const positions = portfolio.positions || [];

  return (
    <section className="brain-accounting-card">
      <div className="section-title">
        <span></span>
        <h2>💰 Live Portfolio</h2>
      </div>

      <div className="brain-grid compact">
        <div className="brain-card">
          <span>SOL Balance</span>
          <strong>{Number(portfolio.sol_balance || 0).toFixed(6)}</strong>
        </div>

        <div className="brain-card">
          <span>USDC</span>
          <strong>{Number(portfolio.usdc_balance || 0).toFixed(4)}</strong>
        </div>

        <div className="brain-card">
          <span>Open Positions</span>
          <strong>{portfolio.open_positions ?? 0}</strong>
        </div>

        <div className="brain-card">
          <span>Today P&amp;L</span>
          <strong>
            ${Number(portfolio.today_pnl_usd || 0).toFixed(2)}
          </strong>
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="alpha-thought-box" style={{ marginTop: "14px" }}>
          <span>No positions</span>
          <p>Alpha has no active trades.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "12px", marginTop: "14px" }}>
          {positions.map((position, index) => (
            <div className="brain-card" key={position.mint || index}>
              <h3 style={{ marginBottom: 10 }}>
                {position.symbol || "UNKNOWN"}
              </h3>

              <p>
                <strong>Quantity:</strong>{" "}
                {Number(position.quantity || 0).toFixed(2)}
              </p>

              <p>
                <strong>Entry:</strong> $
                {Number(position.entry_price || 0).toFixed(8)}
              </p>

              <p>
                <strong>Current:</strong> $
                {Number(position.current_price || 0).toFixed(8)}
              </p>

              <p>
                <strong>Position Value:</strong> $
                {Number(position.current_value_usd || 0).toFixed(4)}
              </p>

              <p>
                <strong>P&amp;L:</strong>{" "}
                <span
                  style={{
                    color:
                      Number(position.pnl_percent || 0) >= 0
                        ? "#22c55e"
                        : "#ef4444",
                  }}
                >
                  {Number(position.pnl_percent || 0).toFixed(2)}%
                </span>
              </p>

              <p>
                <strong>Score:</strong> {position.entry_score}
              </p>

              <p>
                <strong>Probability:</strong> {position.probability}%
              </p>

              <p>
                <strong>Risk:</strong> {position.risk_score}
              </p>

              <p
                style={{
                  opacity: 0.8,
                  fontSize: 13,
                  marginTop: 10,
                }}
              >
                {position.reason}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}