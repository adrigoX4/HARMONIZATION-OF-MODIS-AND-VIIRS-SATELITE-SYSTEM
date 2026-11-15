import React, { useEffect } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'

/**
 * Count-up number animation (V28-style data reveal).
 * Pass a numeric `value`; it springs from 0 to the target whenever the value changes.
 * `decimals` controls fixed-decimal formatting; non-numeric fallbacks render as-is.
 */
export default function AnimatedNumber({ value, decimals = 0, className, style }) {
  const numeric = typeof value === 'number' && Number.isFinite(value) ? value : null

  const motionValue = useMotionValue(0)
  const spring = useSpring(motionValue, { stiffness: 90, damping: 22, mass: 0.8 })
  const display = useTransform(spring, (v) =>
    numeric === null ? String(value) : v.toFixed(decimals)
  )

  useEffect(() => {
    if (numeric !== null) motionValue.set(numeric)
  }, [numeric, motionValue])

  if (numeric === null) {
    return (
      <span className={className} style={style}>
        {value}
      </span>
    )
  }

  return (
    <motion.span className={className} style={style}>
      {display}
    </motion.span>
  )
}
