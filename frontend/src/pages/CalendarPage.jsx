import React from 'react'
import { motion } from 'framer-motion'
import BurningCalendar from '../calendar/BurningCalendar.jsx'

export default function CalendarPage({ days = [] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 25 }}
      className="bento-card"
    >
      <div className="card-header">
        <div>
          <div className="card-title">Dual-Layer Burning Calendar</div>
          <div className="card-sub">Click any calendar day cell to inspect MODIS vs. VIIRS counts, radiative energy (MW), and active H3 hexagons</div>
        </div>
      </div>
      <BurningCalendar days={days} />
    </motion.div>
  )
}