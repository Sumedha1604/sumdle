import { useCallback, useEffect, useMemo, useState } from 'react'
import GameBoard from './components/GameBoard.jsx'
import GameKeyboard from './components/GameKeyboard.jsx'
import GameResult from './components/GameResult.jsx'
import StatsModal from './components/StatsModal.jsx'
import ThemeToggle from './components/ThemeToggle.jsx'
import Mascot from './components/Mascot.jsx'
import ModeToggle from './components/ModeToggle.jsx'
import Tooltip from './components/Tooltip.jsx'
import './App.css'

const MAX_ROWS = 6
const REVEAL_DURATION = 820
const GAME_MODE = { daily: 'daily', unlimited: 'unlimited' }
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const keyPriority = { unused: 0, absent: 1, present: 2, correct: 3 }
const GAME_STATUS = { playing: 'playing', won: 'won', lost: 'lost' }

function HelpIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.45 9.15a2.68 2.68 0 1 1 4.42 2.05c-.98.84-1.87 1.4-1.87 2.8" /><path d="M12 16.9h.01" /></svg>
}

function StatsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V10" /><path d="M12 19V5" /><path d="M19 19v-7" /></svg>
}

function App() {
  const [gameMode, setGameMode] = useState(GAME_MODE.daily)
  const [solution, setSolution] = useState('')
  const [gameId, setGameId] = useState('')
  const [currentRow, setCurrentRow] = useState(0)
  const [currentGuess, setCurrentGuess] = useState('')
  const [submittedGuesses, setSubmittedGuesses] = useState([])
  const [message, setMessage] = useState('')
  const [gameStatus, setGameStatus] = useState(GAME_STATUS.playing)
  const [showResult, setShowResult] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [playerId] = useState(() => {
    const key = 'sumdle_player_id'
    const existing = window.localStorage.getItem(key)
    if (existing) return existing
    const id = crypto.randomUUID()
    window.localStorage.setItem(key, id)
    return id
  })
  const [stats, setStats] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsError, setStatsError] = useState(false)
  const [hint, setHint] = useState('')
  const [hintCount, setHintCount] = useState(0)
  const [definition, setDefinition] = useState(null)
  const [theme, setTheme] = useState(() => window.localStorage.getItem('sumdle_theme') || 'system')
  const [showHelp, setShowHelp] = useState(false)

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const applyTheme = () => { document.documentElement.dataset.theme = theme === 'system' ? (query.matches ? 'dark' : 'light') : theme }
    applyTheme()
    query.addEventListener('change', applyTheme)
    window.localStorage.setItem('sumdle_theme', theme)
    return () => query.removeEventListener('change', applyTheme)
  }, [theme])

  const resetGame = useCallback(() => {
    setCurrentRow(0)
    setCurrentGuess('')
    setSubmittedGuesses([])
    setMessage('')
    setGameStatus(GAME_STATUS.playing)
    setShowResult(false)
  }, [])

  const applyGame = useCallback((game) => {
    setGameId(game.game_id); setSubmittedGuesses(game.guesses); setCurrentRow(game.attempts); setGameStatus(game.status); setSolution(game.solution ?? ''); setHintCount(game.hint_count ?? 0)
  }, [])

  const loadPuzzle = useCallback(async (mode) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/games/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId }) })
      if (!response.ok) throw new Error('Puzzle request failed')
      applyGame(await response.json())
    } catch {
      setGameId('')
      setMessage("couldn't load a puzzle right now")
    } finally {
      setIsLoading(false)
    }
  }, [applyGame, playerId])

  useEffect(() => {
    const loadId = window.setTimeout(() => loadPuzzle(GAME_MODE.daily), 0)
    return () => window.clearTimeout(loadId)
  }, [loadPuzzle])

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/players`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId }) }).catch(() => {})
  }, [playerId])

  const loadStats = useCallback(async () => {
    setStatsLoading(true); setStatsError(false)
    try {
      const response = await fetch(`${API_BASE_URL}/api/players/${encodeURIComponent(playerId)}/stats`)
      if (!response.ok) throw new Error('Stats request failed')
      setStats(await response.json())
    } catch { setStatsError(true) } finally { setStatsLoading(false) }
  }, [playerId])

  const openStats = useCallback(() => { setShowStats(true); loadStats() }, [loadStats])

  const switchMode = useCallback((mode) => {
    if (mode === gameMode) return
    resetGame()
    setGameMode(mode)
    loadPuzzle(mode)
  }, [gameMode, loadPuzzle, resetGame])

  const submitGuess = useCallback(async () => {
    if (isLoading || isSubmitting || gameStatus !== GAME_STATUS.playing || currentGuess.length !== 5 || !gameId) return
    const guess = currentGuess.toLowerCase()
    setIsSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/games/${encodeURIComponent(gameId)}/guess`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ guess }) })
      if (!response.ok) throw new Error('Validation request failed')
      const game = await response.json()
      if (!game.accepted) {
        setMessage(game.message)
        return
      }
      applyGame(game)
      setCurrentGuess('')
      if (game.stats) setStats(game.stats)
    } catch {
      setMessage('could not check that word right now')
    } finally {
      setIsSubmitting(false)
    }
  }, [applyGame, currentGuess, gameId, gameStatus, isLoading, isSubmitting])

  const requestHint = useCallback(async () => {
    if (!gameId || hintCount >= 2 || isSubmitting) return
    setIsSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/games/${encodeURIComponent(gameId)}/hint?level=${hintCount + 1}`)
      const result = await response.json()
      if (!response.ok) throw new Error('Hint request failed')
      setHint(result.hint); setHintCount(result.hint_count)
    } catch { setHint('tiny hints are taking a little break ✦') } finally { setIsSubmitting(false) }
  }, [gameId, hintCount, isSubmitting])

  const handleInput = useCallback((key) => {
    if (isLoading || isSubmitting || gameStatus !== GAME_STATUS.playing || currentRow >= MAX_ROWS) return
    if (key === 'Backspace') setCurrentGuess((guess) => guess.slice(0, -1))
    else if (key === 'Enter') submitGuess()
    else if (/^[a-z]$/i.test(key)) setCurrentGuess((guess) => (guess.length < 5 ? `${guess}${key.toUpperCase()}` : guess))
  }, [currentRow, gameStatus, isLoading, isSubmitting, submitGuess])

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (event.key === 'Backspace') { event.preventDefault(); handleInput('Backspace') }
      else if (event.key === 'Enter') handleInput('Enter')
      else if (/^[a-z]$/i.test(event.key)) handleInput(event.key)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleInput])

  useEffect(() => {
    if (!message) return undefined
    const timeoutId = window.setTimeout(() => setMessage(''), 2200)
    return () => window.clearTimeout(timeoutId)
  }, [message])

  useEffect(() => {
    if (gameStatus === GAME_STATUS.playing) return undefined
    const timeoutId = window.setTimeout(() => setShowResult(true), REVEAL_DURATION)
    return () => window.clearTimeout(timeoutId)
  }, [gameStatus])

  useEffect(() => {
    if (gameStatus === GAME_STATUS.playing || !gameId) return
    fetch(`${API_BASE_URL}/api/games/${encodeURIComponent(gameId)}/definition`)
      .then((response) => response.ok ? response.json() : { available: false })
      .then(setDefinition).catch(() => setDefinition({ available: false }))
  }, [gameId, gameStatus])

  const playAgain = useCallback(() => {
    if (gameMode === GAME_MODE.unlimited) {
      resetGame()
      loadPuzzle(GAME_MODE.unlimited)
    } else switchMode(GAME_MODE.unlimited)
  }, [gameMode, loadPuzzle, resetGame, switchMode])

  const keyStates = useMemo(() => submittedGuesses.reduce((states, guess) => {
    guess.word.toUpperCase().split('').forEach((letter, index) => {
      const state = guess.result[index]
      if (keyPriority[state] > keyPriority[states[letter] ?? 'unused']) states[letter] = state
    })
    return states
  }, {}), [submittedGuesses])

  const mascotState = gameStatus === GAME_STATUS.won ? 'win' : gameStatus === GAME_STATUS.lost ? 'loss' : hint ? 'hint' : currentGuess ? 'typing' : 'idle'

  return <main className="game-shell">
    <div className="atmosphere atmosphere-pink" aria-hidden="true" /><div className="atmosphere atmosphere-lavender" aria-hidden="true" />
    <header className="game-header"><div className="brand" aria-label="Sumdle: a tiny daily word game"><span className="brand-flower" aria-hidden="true">✿</span><span className="brand-sparkle" aria-hidden="true">✦</span><h1>SUMDLE</h1><p>a tiny daily word game</p><span className="brand-heart" aria-hidden="true">♡</span><span className="brand-petal" aria-hidden="true">✦</span></div><div className="header-actions"><ThemeToggle theme={theme} onChange={setTheme} /><Tooltip label="How to play"><button className="circle-button" type="button" aria-label="How to play" onClick={() => setShowHelp(true)}><HelpIcon /></button></Tooltip><Tooltip className="tooltip--edge-right" label="Statistics"><button className="circle-button" type="button" aria-label="View statistics" onClick={openStats}><StatsIcon /></button></Tooltip></div></header>
    <section className="game-card" aria-label="Sumdle game board"><div className="card-decoration decoration-top" aria-hidden="true">✦</div><div className="card-decoration decoration-bottom" aria-hidden="true">✿</div>
      <ModeToggle gameMode={gameMode} onChange={switchMode} />
      <p className="status-strip">{isLoading ? 'loading puzzle...' : gameMode === GAME_MODE.daily ? "today's puzzle" : 'unlimited puzzle'} <span>·</span> 5 letters</p>
      <p className={`game-message${message ? ' game-message--visible' : ''}`} role="status" aria-live="polite">{message}</p>
      {gameStatus !== GAME_STATUS.playing && !showResult && <button className="view-results-button" type="button" onClick={() => setShowResult(true)}>results ♡</button>}
      <div className="board-area"><GameBoard currentGuess={currentGuess} currentRow={currentRow} submittedGuesses={submittedGuesses} /></div>
      {gameStatus === GAME_STATUS.playing && <div className="hint-area"><button className={`hint-button${hintCount < 2 && !hint ? ' hint-button--available' : ''}`} type="button" onClick={requestHint} disabled={isLoading || isSubmitting || hintCount >= 2}>{hintCount >= 2 ? 'all tiny hints used' : `hint ${hintCount ? '(one more)' : ''}`}</button>{hint && <div className="hint-toast-row"><Mascot state={mascotState} /><p className="hint-toast" role="status"><strong>tiny hint ✦</strong>{hint}</p></div>}</div>}
      <GameKeyboard disabled={isLoading || isSubmitting || gameStatus !== GAME_STATUS.playing || !gameId} keyStates={keyStates} onKeyPress={handleInput} />
      <footer className="game-footer">made with <span aria-label="love">♡</span></footer>
    </section>
    {showResult && <GameResult attempts={submittedGuesses.length} definition={definition} gameMode={gameMode} gameStatus={gameStatus} onPlayAgain={playAgain} onViewPuzzle={() => setShowResult(false)} solution={solution} streak={gameMode === GAME_MODE.daily ? stats?.current_streak : null} />}
    {showStats && <StatsModal error={statsError} loading={statsLoading} onClose={() => setShowStats(false)} stats={stats} />}
    {showHelp && <div className="result-overlay" onMouseDown={() => setShowHelp(false)}><section className="result-card help-card" role="dialog" aria-modal="true" aria-labelledby="help-title" onMouseDown={(event) => event.stopPropagation()}><Tooltip className="modal-close-tooltip" label="Close help"><button className="stats-close" type="button" aria-label="Close help" onClick={() => setShowHelp(false)}>×</button></Tooltip><p className="result-kicker">how to play</p><h2 id="help-title">find the tiny word</h2><p className="result-copy">Guess the five-letter word in six tries. After each guess, the tiles show how close you are.</p><div className="help-legend" aria-label="Tile result legend"><div className="help-legend-item"><span className="tile tile--correct help-tile" aria-hidden="true">A</span><span>right spot</span></div><div className="help-legend-item"><span className="tile tile--present help-tile" aria-hidden="true">A</span><span>wrong spot</span></div><div className="help-legend-item"><span className="tile tile--absent help-tile" aria-hidden="true">A</span><span>not in word</span></div></div></section></div>}
  </main>
}

export default App
