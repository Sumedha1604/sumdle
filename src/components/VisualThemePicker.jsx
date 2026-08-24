import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
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
  const triggerRef = useRef(null)
  const popoverRef = useRef(null)
  const [position, setPosition] = useState(null)

  const updatePosition = () => {
    const rect = triggerRef.current?.getBoundingClientRect()
    if (!rect) return
    const mobile = window.matchMedia('(max-width: 47.99rem)').matches
    setPosition(mobile
      ? { top: `${Math.min(rect.bottom + 8, window.innerHeight - 8)}px`, left: '50%', transform: 'translateX(-50%)' }
      : { top: `${rect.bottom + 8}px`, left: `${Math.max(16, Math.min(rect.right - 198, window.innerWidth - 214))}px` })
  }

  useLayoutEffect(() => {
    if (!open) return undefined
    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const closeOnOutsidePress = (event) => {
      if (!pickerRef.current?.contains(event.target) && !popoverRef.current?.contains(event.target)) setOpen(false)
    }
    const closeOnEscape = (event) => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', closeOnOutsidePress)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePress)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  return <div ref={pickerRef} className="visual-theme-picker">
    <Tooltip label="Choose visual theme">
      <button ref={triggerRef} aria-expanded={open} aria-haspopup="dialog" aria-label="Choose visual theme" className="circle-button visual-theme-trigger" onClick={() => setOpen((value) => !value)} type="button"><PaletteIcon /></button>
    </Tooltip>
    {open && position && createPortal(<section ref={popoverRef} aria-label="Choose your theme" className="visual-theme-popover visual-theme-popover--portal" role="dialog" style={position}>
      <p>choose your theme</p>
      <div className="visual-theme-options">
        {visualThemes.map((option) => <button aria-pressed={theme === option.id} className={`visual-theme-option visual-theme-option--${option.id}${theme === option.id ? ' visual-theme-option--active' : ''}`} key={option.id} onClick={() => { onChange(option.id); setOpen(false) }} type="button">
          <span aria-hidden="true" className="visual-theme-swatches"><i /><i /><i /></span>
          <span>{option.label}</span>
        </button>)}
      </div>
    </section>, document.body)}
  </div>
}

export default VisualThemePicker
