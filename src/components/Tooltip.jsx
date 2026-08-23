import { useId } from 'react'

function Tooltip({ children, className = '', label, placement = 'bottom' }) {
  const tooltipId = useId()

  return <span className={`tooltip tooltip--${placement}${className ? ` ${className}` : ''}`}>
    {children}
    <span className="tooltip-content" id={tooltipId} role="tooltip">{label}</span>
  </span>
}

export default Tooltip
