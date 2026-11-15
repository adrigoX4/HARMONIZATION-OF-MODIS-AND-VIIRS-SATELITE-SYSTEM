// One number format across the console: en-US grouping, fixed decimals.
export const fmtNum = (value, decimals = 0) => {
  const n = Number(value)
  if (!Number.isFinite(n)) return 'n/a'
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// Compact axis / cell labels: 1.2M, 48k, 312
export const fmtCompact = (value) => {
  const n = Number(value) || 0
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `${Math.round(n / 1e3)}k`
  return String(Math.round(n))
}
