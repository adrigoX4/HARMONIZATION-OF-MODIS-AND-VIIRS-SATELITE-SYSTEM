import React, { useState } from 'react'
import { motion } from 'framer-motion'
import DayDetailDrawer from './DayDetailDrawer.jsx'

export default function BurningCalendar({ days = [] }) {
  const [selectedDay, setSelectedDay] = useState(null)

  if (!days.length) {
    return <div className="card-sub">No calendar days available in current dataset window.</div>
  }

  const maxCount = Math.max(...days.map((d) => d.total_detections ?? d.count ?? 1), 1)

  return (
    <div>
      <div className="calendar-grid">
        {days.map((day, idx) => {
          const count = day.total_detections ?? day.count ?? 0
          const intensity = Math.min(1, count / maxCount)
          const bg =
            count === 0
              ? 'rgba(15, 23, 42, 0.72)'
              : `rgba(255, 94, 58, ${0.15 + intensity * 0.52})`

          return (
            <motion.div
              key={day.utc_date || day.date || idx}
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.025, type: 'spring', stiffness: 320, damping: 24 }}
              whileHover={{ y: -4, scale: 1.03, borderColor: '#ff5e3a' }}
              className="calendar-cell"
              style={{ background: bg }}
              onClick={() => setSelectedDay(day)}
            >
              <div style={{ fontSize: '0.73rem', fontWeight: 700, color: '#cbd5e1' }}>
                {day.utc_date || day.date}
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.2rem' }}>{count}</div>
              <div style={{ fontSize: '0.7rem', color: '#e2e8f0' }}>
                {Number(day.total_frp_mw ?? day.total_frp ?? 0).toFixed(0)} MW
              </div>
            </motion.div>
          )
        })}
      </div>

      <DayDetailDrawer day={selectedDay} onClose={() => setSelectedDay(null)} />
    </div>
  )
}