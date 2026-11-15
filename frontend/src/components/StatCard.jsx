import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'
import AnimatedNumber from './AnimatedNumber.jsx'

export const cardVariants = {
  hidden: { opacity: 0, y: 18, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 320, damping: 24 },
  },
}

// Splits a string like "680.14 MW" into { numeric: 680.14, suffix: " MW", decimals: 2 }
function splitNumeric(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return { numeric: value, suffix: '', decimals: 0 }
  }
  if (typeof value === 'string') {
    const match = value.match(/^(-?[\d.]+)(.*)$/)
    if (match) {
      const numStr = match[1]
      const decimals = numStr.includes('.') ? numStr.split('.')[1].length : 0
      return { numeric: parseFloat(numStr), suffix: match[2], decimals }
    }
  }
  return null
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  hero = false,
  badge,
}) {
  const parts = splitNumeric(value)

  return (
    <motion.div
      variants={cardVariants}
      whileHover={{ y: -5, scale: 1.015 }}
      transition={{ type: 'spring', stiffness: 360, damping: 22 }}
      className={`bento-card ${hero ? 'hero-gradient' : ''}`}
    >
      <div className="card-header" style={{ marginBottom: '0.4rem' }}>
        <span className="card-sub" style={{ fontWeight: 600 }}>
          {title}
        </span>
        <motion.div
          whileHover={{ rotate: 8, scale: 1.08 }}
          style={{
            width: 32,
            height: 32,
            borderRadius: '10px',
            background: hero ? 'rgba(255,255,255,0.2)' : 'rgba(255,94,58,0.14)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: hero ? '#ffffff' : '#ff5e3a',
          }}
        >
          {Icon ? <Icon size={16} /> : <ArrowUpRight size={16} />}
        </motion.div>
      </div>

      <div className="stat-value">
        {parts ? (
          <>
            <AnimatedNumber value={parts.numeric} decimals={parts.decimals} />
            {parts.suffix}
          </>
        ) : (
          value
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginTop: '0.25rem' }}>
        <span className="card-sub">{subtitle}</span>
        {badge}
      </div>
    </motion.div>
  )
}
