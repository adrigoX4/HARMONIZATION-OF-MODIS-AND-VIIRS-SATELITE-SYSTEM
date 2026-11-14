import React from 'react'
import { motion } from 'framer-motion'
import SensorComparisonChart from '../charts/SensorComparisonChart.jsx'
import AnomalyTimelineChart from '../charts/AnomalyTimelineChart.jsx'

export default function AnalyticsPage({ calendarDays = [] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 25 }}
      className="grid-2"
    >
      <div className="bento-card">
        <div className="card-header">
          <div>
            <div className="card-title">Cross-Sensor Detection Count Ratio</div>
            <div className="card-sub">Illustrates why raw VIIRS (375 m) counts exceed MODIS (1 km) before Layer-1 GLM calibration</div>
          </div>
        </div>
        <SensorComparisonChart days={calendarDays} />
      </div>

      <div className="bento-card">
        <div className="card-header">
          <div>
            <div className="card-title">Total Fire Radiative Power (MW) Curve</div>
            <div className="card-sub">Energy-based aggregation remains more stable across sensor resolutions</div>
          </div>
        </div>
        <AnomalyTimelineChart days={calendarDays} />
      </div>
    </motion.div>
  )
}