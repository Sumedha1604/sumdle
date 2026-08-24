import forestHintLeaf from '../assets/mascot/forest-hint-leaf.png'

function HintFlower({ decoration = { kind: 'flower' }, state = 'idle' }) {
  if (decoration.kind === 'leaf') return <img aria-hidden="true" className={`forest-leaf-friend forest-leaf-friend--${state}`} src={forestHintLeaf} alt="" />
  if (decoration.kind !== 'flower') return <span aria-hidden="true" className={`hint-theme-marker hint-theme-marker--${decoration.kind} hint-theme-marker--${state}`}>{decoration.symbol}</span>

  return (
    <span className={`hint-flower hint-flower--${state}`} aria-hidden="true">
      <span className="mascot-petal mascot-petal--one" /><span className="mascot-petal mascot-petal--two" />
      <span className="mascot-petal mascot-petal--three" /><span className="mascot-petal mascot-petal--four" />
      <span className="mascot-face">•ᴗ•</span><span className="mascot-stem" />
    </span>
  )
}

export default HintFlower
