import { useCallback, useEffect, useMemo, useState } from 'react'
import GameBoard from './components/GameBoard.jsx'
import GameKeyboard from './components/GameKeyboard.jsx'
import GameResult from './components/GameResult.jsx'
import { SOLUTIONS, VALID_GUESSES } from './data/words.js'
import { evaluateGuess } from './utils/evaluateGuess.js'
import './App.css'

const MAX_ROWS = 6
const REVEAL_DURATION = 820
const SOLUTION = SOLUTIONS[0]
const keyPriority = { unused: 0, absent: 1, present: 2, correct: 3 }
const GAME_STATUS = { playing: 'playing', won: 'won', lost: 'lost' }

function HelpIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.45 9.15a2.68 2.68 0 1 1 4.42 2.05c-.98.84-1.87 1.4-1.87 2.8" /><path d="M12 16.9h.01" /></svg>
}

function SettingsIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.03 2.03-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.1h-2.87v-.1a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.03-2.03.06-.06A1.7 1.7 0 0 0 7.33 15 1.7 1.7 0 0 0 5.77 14h-.1v-2.87h.1a1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.03-2.03.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56v-.1h2.87v.1a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.03 2.03-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1.03h.1V14h-.1A1.7 1.7 0 0 0 19.4 15Z" /></svg>
}

function App() {
  const [currentRow, setCurrentRow] = useState(0)
  const [currentGuess, setCurrentGuess] = useState('')
  const [submittedGuesses, setSubmittedGuesses] = useState([])
  const [message, setMessage] = useState('')
  const [gameStatus, setGameStatus] = useState(GAME_STATUS.playing)
  const [showResult, setShowResult] = useState(false)

  const submitGuess = useCallback(() => {
    if (gameStatus !== GAME_STATUS.playing || currentGuess.length !== 5) return

    const guess = currentGuess.toLowerCase()
    if (!VALID_GUESSES.includes(guess)) {
      setMessage('not in the word list')
      return
    }

    setSubmittedGuesses((guesses) => [...guesses, { word: guess, result: evaluateGuess(guess, SOLUTION) }])
    setCurrentGuess('')
    setCurrentRow((row) => row + 1)

    if (guess === SOLUTION) {
      setGameStatus(GAME_STATUS.won)
    } else if (currentRow === MAX_ROWS - 1) {
      setGameStatus(GAME_STATUS.lost)
    }
  }, [currentGuess, currentRow, gameStatus])

  const handleInput = useCallback((key) => {
    if (gameStatus !== GAME_STATUS.playing || currentRow >= MAX_ROWS) return

    if (key === 'Backspace') {
      setCurrentGuess((guess) => guess.slice(0, -1))
      return
    }

    if (key === 'Enter') {
      submitGuess()
      return
    }

    if (/^[a-z]$/i.test(key)) {
      setCurrentGuess((guess) => (guess.length < 5 ? `${guess}${key.toUpperCase()}` : guess))
    }
  }, [currentRow, gameStatus, submitGuess])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.metaKey || event.ctrlKey || event.altKey) return

      if (event.key === 'Backspace') {
        event.preventDefault()
        handleInput('Backspace')
        return
      }

      if (event.key === 'Enter') {
        handleInput('Enter')
        return
      }

      if (/^[a-z]$/i.test(event.key)) {
        handleInput(event.key)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleInput])

  useEffect(() => {
    if (!message) return undefined

    const timeoutId = window.setTimeout(() => setMessage(''), 1800)
    return () => window.clearTimeout(timeoutId)
  }, [message])

  useEffect(() => {
    if (gameStatus === GAME_STATUS.playing) return undefined

    const timeoutId = window.setTimeout(() => setShowResult(true), REVEAL_DURATION)
    return () => window.clearTimeout(timeoutId)
  }, [gameStatus])

  const restartGame = useCallback(() => {
    setCurrentRow(0)
    setCurrentGuess('')
    setSubmittedGuesses([])
    setMessage('')
    setGameStatus(GAME_STATUS.playing)
    setShowResult(false)
  }, [])

  const keyStates = useMemo(() => submittedGuesses.reduce((states, guess) => {
    guess.word.toUpperCase().split('').forEach((letter, index) => {
      const state = guess.result[index]
      if (keyPriority[state] > keyPriority[states[letter] ?? 'unused']) states[letter] = state
    })
    return states
  }, {}), [submittedGuesses])

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
        <p className={`game-message${message ? ' game-message--visible' : ''}`} role="status" aria-live="polite">{message}</p>
        <div className="board-area" aria-label="Empty six by five word board">
          <GameBoard currentGuess={currentGuess} currentRow={currentRow} submittedGuesses={submittedGuesses} />
        </div>
        <GameKeyboard disabled={gameStatus !== GAME_STATUS.playing} keyStates={keyStates} onKeyPress={handleInput} />
        <footer className="game-footer">made with <span aria-label="love">♡</span></footer>
      </section>
      {showResult && <GameResult attempts={submittedGuesses.length} gameStatus={gameStatus} onPlayAgain={restartGame} solution={SOLUTION} />}
    </main>
  )
}

export default App
