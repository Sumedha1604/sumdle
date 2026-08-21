import './App.css'

const rows = Array.from({ length: 6 })
const columns = Array.from({ length: 5 })

function HelpIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.45 9.15a2.68 2.68 0 1 1 4.42 2.05c-.98.84-1.87 1.4-1.87 2.8" /><path d="M12 16.9h.01" /></svg>
}

function SettingsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.03 2.03-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.1h-2.87v-.1a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.03-2.03.06-.06A1.7 1.7 0 0 0 7.33 15 1.7 1.7 0 0 0 5.77 14h-.1v-2.87h.1a1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.03-2.03.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56v-.1h2.87v.1a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.03 2.03-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1.03h.1V14h-.1A1.7 1.7 0 0 0 19.4 15Z" /></svg>
}

function App() {
  return (
    <main className="game-shell">
      <div className="atmosphere atmosphere-pink" aria-hidden="true" />
      <div className="atmosphere atmosphere-lavender" aria-hidden="true" />
      <header className="game-header">
        <button className="circle-button" type="button" aria-label="How to play"><HelpIcon /></button>
        <div className="brand" aria-label="Sumdle: a tiny daily word game">
          <span className="brand-flower" aria-hidden="true">✿</span><span className="brand-sparkle" aria-hidden="true">✦</span>
          <h1>SUMDLE</h1>
          <span className="brand-heart" aria-hidden="true">♡</span><span className="brand-petal" aria-hidden="true">✦</span>
        </div>
        <button className="circle-button" type="button" aria-label="Game settings"><SettingsIcon /></button>
      </header>
      <section className="game-card" aria-label="Sumdle game board">
        <div className="card-decoration decoration-top" aria-hidden="true">✦</div>
        <div className="card-decoration decoration-bottom" aria-hidden="true">✿</div>
        <p className="game-subtitle">a tiny daily word game</p>
        <p className="status-strip">today's puzzle <span>·</span> 5 letters</p>
        <div className="board-area" aria-label="Empty six by five word board">
          <div className="game-board">
            {rows.map((_, rowIndex) => columns.map((_, columnIndex) => <div className="tile" key={`${rowIndex}-${columnIndex}`} aria-hidden="true" />))}
          </div>
        </div>
        <footer className="game-footer">made with <span aria-label="love">♡</span></footer>
      </section>
    </main>
  )
}

export default App
