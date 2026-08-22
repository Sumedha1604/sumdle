function StatsModal({ error, loading, onClose, stats }) {
  const distribution = stats?.guess_distribution ?? {}
  const max = Math.max(1, ...Object.values(distribution))

  return (
    <div className="result-overlay stats-overlay" onMouseDown={onClose}>
      <section className="result-card stats-card" role="dialog" aria-modal="true" aria-labelledby="stats-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="stats-close" type="button" aria-label="Close statistics" onClick={onClose}>×</button>
        <p className="result-kicker">your tiny record</p><h2 id="stats-title">statistics ✦</h2>
        {loading ? <p className="stats-state">gathering your little wins...</p> : error ? <p className="stats-state">stats are taking a small break. your game is still safe to play.</p> : <>
          <div className="stats-summary"><div><strong>{stats.games_played}</strong><span>Played</span></div><div><strong>{stats.win_percentage}%</strong><span>Win %</span></div><div><strong>{stats.current_streak}</strong><span>Current<br />Streak</span></div><div><strong>{stats.max_streak}</strong><span>Max<br />Streak</span></div></div>
          <h3>guess distribution</h3>
          <div className="guess-distribution">{[1, 2, 3, 4, 5, 6].map((guess) => <div className="distribution-row" key={guess}><b>{guess}</b><div className="distribution-track"><span style={{ width: `${distribution[String(guess)] ? Math.max(12, distribution[String(guess)] / max * 100) : 0}%` }}>{distribution[String(guess)] || ''}</span></div></div>)}</div>
          <p className="stats-note">Anonymous stats stay with this browser.</p>
        </>}
      </section>
    </div>
  )
}

export default StatsModal
