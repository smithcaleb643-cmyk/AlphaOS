export default function LivePortfolioPanel({ livePortfolio }) {
  const portfolio = livePortfolio || {};
  const tokens = portfolio.tokens || [];

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
          <span>Today P&L</span>
          <strong>${Number(portfolio.today_pnl_usd || 0).toFixed(2)}</strong>
        </div>
      </div>

      {tokens.length === 0 ? (
        <div className="alpha-thought-box" style={{ marginTop: "14px" }}>
          <span>No tokens detected</span>
          <p>Alpha will show live token positions here.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "10px", marginTop: "14px" }}>
          {tokens.map((token, index) => (
            <div className="brain-card" key={token.mint || index}>
              <span>{token.symbol || token.mint || "Token"}</span>
              <strong>{token.amount ?? token.balance ?? 0}</strong>
              <p style={{ wordBreak: "break-all" }}>{token.mint}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}