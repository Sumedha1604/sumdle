export function evaluateGuess(guess, solution) {
  const result = Array(guess.length).fill('absent')
  const remainingSolution = solution.split('')

  for (let index = 0; index < guess.length; index += 1) {
    if (guess[index] === solution[index]) {
      result[index] = 'correct'
      remainingSolution[index] = null
    }
  }

  for (let index = 0; index < guess.length; index += 1) {
    if (result[index] === 'correct') continue

    const matchIndex = remainingSolution.indexOf(guess[index])
    if (matchIndex !== -1) {
      result[index] = 'present'
      remainingSolution[matchIndex] = null
    }
  }

  return result
}
