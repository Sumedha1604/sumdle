function HintFlower({ decoration = { kind: 'flower' }, state = 'idle' }) {
  if (decoration.kind === 'sprout') return <span aria-hidden="true" className={`forest-sprout forest-sprout--${state}`}><i className="forest-sprout-leaf forest-sprout-leaf--left" /><i className="forest-sprout-leaf forest-sprout-leaf--right" /><i className="forest-sprout-stem" /><i className="forest-sprout-ground" /></span>
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
