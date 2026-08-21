function GameResult({ attempts, gameMode, gameStatus, onPlayAgain, solution }) {
  const won = gameStatus === 'won'

  return (
    <div className="result-overlay">
      <section className={`result-card result-card--${gameStatus}`} role="dialog" aria-modal="true" aria-labelledby="result-title">
        {won && <div className="celebration" aria-hidden="true"><span>✦</span><span>♡</span><span>✿</span><span>✦</span></div>}
        <p className="result-kicker">{won ? 'a little win' : gameMode === 'daily' ? 'tomorrow is another try' : 'one more little try?'}</p>
        <h2 id="result-title">{won ? 'you got it ♡' : 'so close'}</h2>
        {won ? (
          <p className="result-copy">You found <strong>{solution.toUpperCase()}</strong> in {attempts} {attempts === 1 ? 'try' : 'tries'}.</p>
        ) : (
          <p className="result-copy">The word was <strong>{solution.toUpperCase()}</strong>.</p>
        )}
        <button className="play-again-button" type="button" onClick={onPlayAgain} autoFocus>{gameMode === 'daily' ? 'try unlimited' : 'play again'}</button>
      </section>
    </div>
  )
}

export default GameResult
