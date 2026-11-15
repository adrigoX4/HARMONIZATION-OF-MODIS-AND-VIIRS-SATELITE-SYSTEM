import React from 'react'
import { motion } from 'framer-motion'
import AnimatedNumber from './AnimatedNumber.jsx'
import { itemVariants } from './motion.js'

/**
 * A label, one figure, one line of meta. `lead` puts the figure in the accent.
 */
export default function StatCard({ title, value, unit, decimals = 0, meta, lead = false }) {
  return (
    <motion.div variants={itemVariants} className={`panel stat-card ${lead ? 'lead' : ''}`}>
      <div className="stat-label">{title}</div>
      <div className="stat-value">
        <AnimatedNumber value={value} decimals={decimals} />
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {meta && <div className="stat-meta">{meta}</div>}
    </motion.div>
  )
}
