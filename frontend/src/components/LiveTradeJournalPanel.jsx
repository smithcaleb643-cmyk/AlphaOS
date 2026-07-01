export default function LiveTradeJournalPanel({ liveJournal }) {
  const trades = liveJournal?.trades || [];

  return (
    <section className="brain-accounting-card">
      <div className="section-title">
        <span></span>
        <h2>📜 Live Trade Journal</h2>
      </div>

      {trades.length === 0 ? (
        <div className="alpha-thought-box">
          <span>No live trades recorded yet</span>
          <p>Alpha will record live buys here after execution.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "12px" }}>
          {trades.slice().reverse().map((trade) => (
            <div className="brain-card" key={trade.id}>
              <span>
                #{trade.id} • {trade.type} • {trade.status}
              </span>

              <strong>
                {trade.sol_amount ?? 0} SOL
              </strong>

              <p style={{ wordBreak: "break-all" }}>
                Token: {trade.token_address || "Unknown"}
              </p>

              <p>
                Value: ${Number(trade.swap_usd_value || 0).toFixed(4)}
              </p>

              <p>
                Price Impact: {Number(trade.price_impact_pct || 0).toFixed(4)}%
              </p>

              <p style={{ wordBreak: "break-all" }}>
                TX: {trade.signature || "No signature"}
              </p>

              <p>
                {trade.created_at}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}