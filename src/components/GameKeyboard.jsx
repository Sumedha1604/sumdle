const keyboardRows = ['QWERTYUIOP', 'ASDFGHJKL', 'ENTERZXCVBNMBACKSPACE']

function BackspaceIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 7-5 5 5 5" /><path d="M5 12h12a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-7" /></svg>
}

function GameKeyboard({ disabled, keyStates, onKeyPress }) {
  return (
    <div className="game-keyboard" aria-label="On-screen keyboard">
      {keyboardRows.map((row) => (
        <div className="keyboard-row" key={row}>
          {[...row.matchAll(/ENTER|BACKSPACE|[A-Z]/g)].map(([key]) => (
            <button
              className={`key key--${keyStates[key] ?? 'unused'}${key.length > 1 ? ' key--wide' : ''}`}
              key={key}
              type="button"
              aria-label={key === 'BACKSPACE' ? 'Backspace' : key === 'ENTER' ? 'Submit guess' : key}
              onClick={() => onKeyPress(key === 'ENTER' ? 'Enter' : key === 'BACKSPACE' ? 'Backspace' : key)}
              disabled={disabled}
            >
              {key === 'BACKSPACE' ? <BackspaceIcon /> : key === 'ENTER' ? 'enter' : key}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

export default GameKeyboard
