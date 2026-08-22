import { useCallback, useEffect, useMemo, useState } from 'react'
import GameBoard from './components/GameBoard.jsx'
import GameKeyboard from './components/GameKeyboard.jsx'
import GameResult from './components/GameResult.jsx'
import StatsModal from './components/StatsModal.jsx'
import { evaluateGuess } from './utils/evaluateGuess.js'
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

function SettingsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.03 2.03-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.1h-2.87v-.1a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.03-2.03.06-.06A1.7 1.7 0 0 0 7.33 15 1.7 1.7 0 0 0 5.77 14h-.1v-2.87h.1a1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.03-2.03.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56v-.1h2.87v.1a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.56 1.03h.1V14h-.1A1.7 1.7 0 0 0 19.4 15Z" /></svg>
}

function StatsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V10" /><path d="M12 19V5" /><path d="M19 19v-7" /></svg>
}

function App() {
  const [gameMode, setGameMode] = useState(GAME_MODE.daily)
  const [solution, setSolution] = useState('')
  const [currentRow, setCurrentRow] = useState(0)
  const [currentGuess, setCurrentGuess] = useState('')
  const [submittedGuesses, setSubmittedGuesses] = useState([])
  const [message, setMessage] = useState('')
  const [gameStatus, setGameStatus] = useState(GAME_STATUS.playing)
  const [showResult, setShowResult] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [puzzleDate, setPuzzleDate] = useState(null)
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

  const resetGame = useCallback(() => {
    setCurrentRow(0)
    setCurrentGuess('')
    setSubmittedGuesses([])
    setMessage('')
    setGameStatus(GAME_STATUS.playing)
    setShowResult(false)
  }, [])

  const loadPuzzle = useCallback(async (mode, previousSolution = '') => {
    setIsLoading(true)
    try {
      const endpoint = mode === GAME_MODE.daily
        ? '/api/puzzle/daily'
        : `/api/puzzle/random${previousSolution ? `?exclude=${encodeURIComponent(previousSolution)}` : ''}`
      const response = await fetch(`${API_BASE_URL}${endpoint}`)
      if (!response.ok) throw new Error('Puzzle request failed')
      const puzzle = await response.json()
      if (!/^[a-z]{5}$/.test(puzzle.solution ?? '')) throw new Error('Invalid puzzle response')
      setSolution(puzzle.solution)
      setPuzzleDate(puzzle.date ?? null)
    } catch {
      setSolution('')
      setMessage("couldn't load a puzzle right now")
    } finally {
      setIsLoading(false)
    }
  }, [])

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
    if (isLoading || isSubmitting || gameStatus !== GAME_STATUS.playing || currentGuess.length !== 5 || !solution) return
    const guess = currentGuess.toLowerCase()
    setIsSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/words/validate/${encodeURIComponent(guess)}`)
      if (!response.ok) throw new Error('Validation request failed')
      const validation = await response.json()
      if (validation.valid !== true) {
        setMessage(validation.source === 'unavailable' ? 'dictionary is taking a little break' : 'not in the word list')
        return
      }
      setSubmittedGuesses((guesses) => [...guesses, { word: guess, result: evaluateGuess(guess, solution) }])
      setCurrentGuess('')
      setCurrentRow((row) => row + 1)
      if (guess === solution) setGameStatus(GAME_STATUS.won)
      else if (currentRow === MAX_ROWS - 1) setGameStatus(GAME_STATUS.lost)
    } catch {
      setMessage('could not check that word right now')
    } finally {
      setIsSubmitting(false)
    }
  }, [currentGuess, currentRow, gameStatus, isLoading, isSubmitting, solution])

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
    if (gameStatus === GAME_STATUS.playing || !solution) return
    const attempts = submittedGuesses.length
    fetch(`${API_BASE_URL}/api/game-results`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, mode: gameMode, attempts, won: gameStatus === GAME_STATUS.won, puzzle_date: puzzleDate, solution }) })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((result) => setStats(result.stats))
      .catch(() => {})
  }, [gameMode, gameStatus, playerId, puzzleDate, solution, submittedGuesses.length])

  const playAgain = useCallback(() => {
    if (gameMode === GAME_MODE.unlimited) {
      resetGame()
      loadPuzzle(GAME_MODE.unlimited, solution)
    } else switchMode(GAME_MODE.unlimited)
  }, [gameMode, loadPuzzle, resetGame, solution, switchMode])

  const keyStates = useMemo(() => submittedGuesses.reduce((states, guess) => {
    guess.word.toUpperCase().split('').forEach((letter, index) => {
      const state = guess.result[index]
      if (keyPriority[state] > keyPriority[states[letter] ?? 'unused']) states[letter] = state
    })
    return states
  }, {}), [submittedGuesses])

  return <main className="game-shell">
    <div className="atmosphere atmosphere-pink" aria-hidden="true" /><div className="atmosphere atmosphere-lavender" aria-hidden="true" />
    <header className="game-header"><button className="circle-button" type="button" aria-label="How to play"><HelpIcon /></button><div className="brand" aria-label="Sumdle: a tiny daily word game"><span className="brand-flower" aria-hidden="true">✿</span><span className="brand-sparkle" aria-hidden="true">✦</span><h1>SUMDLE</h1><span className="brand-heart" aria-hidden="true">♡</span><span className="brand-petal" aria-hidden="true">✦</span></div><div className="header-actions"><button className="circle-button" type="button" aria-label="View statistics" onClick={openStats}><StatsIcon /></button><button className="circle-button" type="button" aria-label="Game settings"><SettingsIcon /></button></div></header>
    <section className="game-card" aria-label="Sumdle game board"><div className="card-decoration decoration-top" aria-hidden="true">✦</div><div className="card-decoration decoration-bottom" aria-hidden="true">✿</div>
      <p className="game-subtitle">a tiny daily word game</p>
      <div className="mode-selector" aria-label="Game mode"><button className={gameMode === GAME_MODE.daily ? 'mode-button mode-button--active' : 'mode-button'} type="button" aria-pressed={gameMode === GAME_MODE.daily} onClick={() => switchMode(GAME_MODE.daily)}>Daily</button><button className={gameMode === GAME_MODE.unlimited ? 'mode-button mode-button--active' : 'mode-button'} type="button" aria-pressed={gameMode === GAME_MODE.unlimited} onClick={() => switchMode(GAME_MODE.unlimited)}>Unlimited</button></div>
      <p className="status-strip">{isLoading ? 'loading puzzle...' : gameMode === GAME_MODE.daily ? "today's puzzle" : 'unlimited puzzle'} <span>·</span> 5 letters</p>
      <p className={`game-message${message ? ' game-message--visible' : ''}`} role="status" aria-live="polite">{message}</p>
      <div className="board-area"><GameBoard currentGuess={currentGuess} currentRow={currentRow} submittedGuesses={submittedGuesses} /></div>
      <GameKeyboard disabled={isLoading || isSubmitting || gameStatus !== GAME_STATUS.playing || !solution} keyStates={keyStates} onKeyPress={handleInput} />
      <footer className="game-footer">made with <span aria-label="love">♡</span></footer>
    </section>
    {showResult && <GameResult attempts={submittedGuesses.length} gameMode={gameMode} gameStatus={gameStatus} onPlayAgain={playAgain} solution={solution} streak={gameMode === GAME_MODE.daily ? stats?.current_streak : null} />}
    {showStats && <StatsModal error={statsError} loading={statsLoading} onClose={() => setShowStats(false)} stats={stats} />}
  </main>
}

export default App
