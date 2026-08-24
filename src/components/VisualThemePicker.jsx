import { useEffect, useRef, useState } from 'react'
import Tooltip from './Tooltip.jsx'

const visualThemes = [
  { id: 'blush', label: 'Blush' },
  { id: 'forest', label: 'Forest' },
  { id: 'classic', label: 'Classic' },
]

function PaletteIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5a8.5 8.5 0 1 0 0 17h1.1a1.9 1.9 0 0 0 1.74-2.65 1.9 1.9 0 0 1 1.74-2.65H17a3.5 3.5 0 0 0 0-7h-1.1A1.9 1.9 0 0 1 14.16 5.5 1.9 1.9 0 0 0 12.42 3.5Z" /><path d="M7.8 10.2h.01M10.2 7.7h.01M14.1 7.8h.01M7.8 14.1h.01" /></svg>
}

function VisualThemePicker({ theme, onChange }) {
  const [open, setOpen] = useState(false)
  const pickerRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const closeOnOutsidePress = (event) => {
      if (!pickerRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsidePress)
    return () => document.removeEventListener('pointerdown', closeOnOutsidePress)
  }, [open])

  return <div ref={pickerRef} className="visual-theme-picker">
    <Tooltip label="Choose visual theme">
      <button aria-expanded={open} aria-haspopup="dialog" aria-label="Choose visual theme" className="circle-button visual-theme-trigger" onClick={() => setOpen((value) => !value)} type="button"><PaletteIcon /></button>
    </Tooltip>
    {open && <section aria-label="Choose your theme" className="visual-theme-popover" role="dialog">
      <p>choose your theme</p>
      <div className="visual-theme-options">
        {visualThemes.map((option) => <button aria-pressed={theme === option.id} className={`visual-theme-option visual-theme-option--${option.id}${theme === option.id ? ' visual-theme-option--active' : ''}`} key={option.id} onClick={() => { onChange(option.id); setOpen(false) }} type="button">
          <span aria-hidden="true" className="visual-theme-swatches"><i /><i /><i /></span>
          <span>{option.label}</span>
        </button>)}
      </div>
    </section>}
  </div>
}

export default VisualThemePicker
