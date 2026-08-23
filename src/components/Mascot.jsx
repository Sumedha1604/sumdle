function Mascot({ state = 'idle' }) {
  return (
    <span className={`mascot mascot--${state}`} aria-hidden="true">
      <span className="mascot-petal mascot-petal--one" /><span className="mascot-petal mascot-petal--two" />
      <span className="mascot-petal mascot-petal--three" /><span className="mascot-petal mascot-petal--four" />
      <span className="mascot-face">•ᴗ•</span><span className="mascot-stem" />
    </span>
  )
}

export default Mascot
