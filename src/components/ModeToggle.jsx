function ModeToggle({ gameMode, onChange }) {
  return <div className="mode-selector" aria-label="Game mode">
    <button className={gameMode === 'daily' ? 'mode-button mode-button--active' : 'mode-button'} type="button" aria-pressed={gameMode === 'daily'} onClick={() => onChange('daily')}>Daily</button>
    <button className={gameMode === 'unlimited' ? 'mode-button mode-button--active' : 'mode-button'} type="button" aria-pressed={gameMode === 'unlimited'} onClick={() => onChange('unlimited')}>Unlimited</button>
  </div>
}

export default ModeToggle
