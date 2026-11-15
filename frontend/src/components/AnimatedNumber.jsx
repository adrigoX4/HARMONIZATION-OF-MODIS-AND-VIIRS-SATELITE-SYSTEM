import React, { useEffect } from 'react'
import { animate, motion, useMotionValue, useTransform } from 'framer-motion'
import { fmtNum } from '../lib/format.js'
import { EASE } from './motion.js'

/**
 * Tweens a figure from its previous value to the new one (no spring, no overshoot).
 * Non-numeric values render as an em dash.
 */
export default function AnimatedNumber({ value, decimals = 0, className = '' }) {
  const numeric = typeof value === 'number' && Number.isFinite(value)
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => fmtNum(v, decimals))

  useEffect(() => {
    if (!numeric) return
    const controls = animate(mv, value, { duration: 0.5, ease: EASE })
    return () => controls.stop()
  }, [value, numeric, mv])

  if (!numeric) return <span className={className}>n/a</span>
  return <motion.span className={`tnum ${className}`}>{display}</motion.span>
}
