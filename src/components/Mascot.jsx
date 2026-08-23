import { useEffect, useState } from 'react'
import mascotStatic from '../assets/mascot/mascot.png'
import mascotCelebrate from '../assets/mascot/mascot-celebrate.png'

const CELEBRATION_DURATION = 1040

function Mascot({ className = '', state = 'idle' }) {
  const [isCelebrating, setIsCelebrating] = useState(state === 'win')

  useEffect(() => {
    if (!isCelebrating) return undefined
    const timeoutId = window.setTimeout(() => setIsCelebrating(false), CELEBRATION_DURATION)
    return () => window.clearTimeout(timeoutId)
  }, [isCelebrating])

  return <span
    aria-hidden="true"
    className={`mascot mascot--${state}${isCelebrating ? ' mascot--celebrating' : ''}${className ? ` ${className}` : ''}`}
    style={{ '--mascot-static': `url(${mascotStatic})`, '--mascot-celebrate': `url(${mascotCelebrate})` }}
  />
}

export default Mascot
