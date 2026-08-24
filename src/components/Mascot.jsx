import { useEffect, useState } from 'react'
import mascotStatic from '../assets/mascot/mascot.png'
import mascotCelebrate from '../assets/mascot/mascot-celebrate.png'

const CELEBRATION_DURATION = 1040

function Mascot({ className = '', decoration = { kind: 'pixel' }, state = 'idle' }) {
  const [isCelebrating, setIsCelebrating] = useState(state === 'win')

  useEffect(() => {
    if (!isCelebrating) return undefined
    const timeoutId = window.setTimeout(() => setIsCelebrating(false), CELEBRATION_DURATION)
    return () => window.clearTimeout(timeoutId)
  }, [isCelebrating])

  if (decoration.kind === 'mushroom') return <span aria-hidden="true" className={`forest-mushroom forest-mushroom--${state}${className ? ` ${className}` : ''}`}><span className="forest-mushroom-cap"><i /><i /><i /></span><span className="forest-mushroom-stem" /></span>
  if (decoration.kind !== 'pixel') return <span aria-hidden="true" className={`theme-companion theme-companion--${decoration.kind} theme-companion--${state}${className ? ` ${className}` : ''}`}>{decoration.symbol}</span>

  return <span
    aria-hidden="true"
    className={`mascot mascot--${state}${isCelebrating ? ' mascot--celebrating' : ''}${className ? ` ${className}` : ''}`}
    style={{ '--mascot-static': `url(${mascotStatic})`, '--mascot-celebrate': `url(${mascotCelebrate})` }}
  />
}

export default Mascot
