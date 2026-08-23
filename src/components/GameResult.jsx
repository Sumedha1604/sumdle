function GameResult({ attempts, definition, gameMode, gameStatus, onPlayAgain, onShare, onViewPuzzle, shareMessage, solution, streak }) {
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
        {won && streak !== null && <p className="result-streak">daily streak: {streak} ✦</p>}
        <section className="word-definition" aria-label="Word definition"><p>word</p>{definition?.available ? <><strong>{solution.toUpperCase()}</strong><span>{definition.part_of_speech}{definition.phonetic ? ` · ${definition.phonetic}` : ''}</span><small>{definition.definition}</small></> : <small>a little definition is taking a break right now.</small>}</section>
        <div className="result-actions"><button className="view-puzzle-button" type="button" onClick={onViewPuzzle}>view puzzle</button><button className="share-result-button" type="button" onClick={onShare}>share result</button><button className="play-again-button" type="button" onClick={onPlayAgain} autoFocus>{gameMode === 'daily' ? 'try unlimited' : 'play again'}</button></div>
        <p className={`share-toast${shareMessage ? ' share-toast--visible' : ''}`} role="status" aria-live="polite">{shareMessage}</p>
      </section>
    </div>
  )
}

export default GameResult
