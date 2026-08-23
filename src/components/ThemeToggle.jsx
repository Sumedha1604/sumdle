const themes = ['light', 'dark', 'system']

function ThemeIcon({ theme }) {
  if (theme === 'dark') return <span aria-hidden="true">☾</span>
  if (theme === 'system') return <span aria-hidden="true">◐</span>
  return <span aria-hidden="true">☼</span>
}

function ThemeToggle({ theme, onChange }) {
  return (
    <div className="theme-control" aria-label="Theme">
      {themes.map((option) => (
        <Tooltip key={option} label={`${option[0].toUpperCase()}${option.slice(1)} theme`}>
          <button
          aria-label={`${option} theme`}
          aria-pressed={theme === option}
          className={`theme-option${theme === option ? ' theme-option--active' : ''}`}
          onClick={() => onChange(option)}
          type="button"
          >
            <ThemeIcon theme={option} />
          </button>
        </Tooltip>
      ))}
    </div>
  )
}

export default ThemeToggle
import Tooltip from './Tooltip.jsx'
