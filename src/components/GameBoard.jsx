const rows = Array.from({ length: 6 })
const columns = Array.from({ length: 5 })

function GameBoard({ currentGuess, currentRow, submittedGuesses }) {
  return (
    <div className="game-board" role="grid" aria-label="Six attempts to guess a five-letter word">
      {rows.map((_, rowIndex) => {
        const submittedGuess = submittedGuesses[rowIndex]
        const guess = submittedGuess?.word?.toUpperCase() ?? (rowIndex === currentRow ? currentGuess : '')

        return columns.map((_, columnIndex) => {
          const letter = guess[columnIndex] ?? ''

          return (
            <div
              className={`tile${letter ? ' tile--filled' : ''}${submittedGuess ? ` tile--${submittedGuess.result[columnIndex]} tile--revealed` : ''}`}
              key={`${rowIndex}-${columnIndex}`}
              role="gridcell"
              aria-label={letter || 'empty'}
              style={submittedGuess ? { animationDelay: `${columnIndex * 95}ms` } : undefined}
            >
              {letter}
            </div>
          )
        })
      })}
    </div>
  )
}

export default GameBoard
