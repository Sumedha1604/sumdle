import { useEffect, useState } from 'react'
import mascotStatic from '../assets/mascot/mascot.png'
import mascotCelebrate from '../assets/mascot/mascot-celebrate.png'
import foxStatic from '../assets/mascot/pixel-art-fox.png'

const CELEBRATION_DURATION = 1040

function Mascot({ className = '', decoration = { kind: 'pixel' }, state = 'idle' }) {
  const [isCelebrating, setIsCelebrating] = useState(state === 'win')

  useEffect(() => {
    if (!isCelebrating) return undefined
    const timeoutId = window.setTimeout(() => setIsCelebrating(false), CELEBRATION_DURATION)
    return () => window.clearTimeout(timeoutId)
  }, [isCelebrating])

  if (decoration.kind === 'fox') return <span aria-hidden="true" className={`forest-fox forest-fox--${state}${className ? ` ${className}` : ''}`} style={{ '--fox-static': `url(${foxStatic})` }} />
  if (decoration.kind !== 'pixel') return <span aria-hidden="true" className={`theme-companion theme-companion--${decoration.kind} theme-companion--${state}${className ? ` ${className}` : ''}`}>{decoration.symbol}</span>

  return <span
    aria-hidden="true"
    className={`mascot mascot--${state}${isCelebrating ? ' mascot--celebrating' : ''}${className ? ` ${className}` : ''}`}
    style={{ '--mascot-static': `url(${mascotStatic})`, '--mascot-celebrate': `url(${mascotCelebrate})` }}
  />
}

export default Mascot
