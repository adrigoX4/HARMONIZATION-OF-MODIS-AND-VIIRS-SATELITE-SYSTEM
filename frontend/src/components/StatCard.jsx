import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'

export const cardVariants = {
  hidden: { opacity: 0, y: 18, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 320, damping: 24 },
  },
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  hero = false,
  badge,
}) {
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
        <div
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
        </div>
      </div>

      <div className="stat-value">{value}</div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginTop: '0.25rem' }}>
        <span className="card-sub">{subtitle}</span>
        {badge}
      </div>
    </motion.div>
  )
}