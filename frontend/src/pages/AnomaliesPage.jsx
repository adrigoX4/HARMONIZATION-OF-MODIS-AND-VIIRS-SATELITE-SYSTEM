import React from 'react'
import { motion } from 'framer-motion'

export default function AnomaliesPage({ anomalyData }) {
  const items = anomalyData?.items || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 25 }}
      className="bento-card"
    >
      <div className="card-header">
        <div>
          <div className="card-title">H3 Hexagon Seasonal Baseline & Anomaly Intelligence</div>
          <div className="card-sub">
            Source: <code>{anomalyData?.source || 'features-preview'}</code> • Scores reflect statistical departure from historical H3 Res-5 seasonal baselines
          </div>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>H3 Hexagon (Res-5)</th>
              <th>UTC Date</th>
              <th>Status</th>
              <th>MODIS / VIIRS</th>
              <th>Max FRP (MW)</th>
              <th>Anomaly Score</th>
              <th>Drivers</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 40).map((row, idx) => (
              <tr key={`${row.h3_index}-${row.utc_date}-${idx}`}>
                <td><code>{row.h3_index}</code></td>
                <td>{row.utc_date}</td>
                <td>
                  <span className={`badge ${row.is_anomaly ? 'badge-anomaly' : 'badge-matched'}`}>
                    {row.baseline_label || (row.is_anomaly ? 'Unusual vs. baseline' : 'Normal')}
                  </span>
                </td>
                <td>{row.modis_count} / {row.viirs_count}</td>
                <td>{Number(row.max_frp || 0).toFixed(1)} MW</td>
                <td><strong>{Number(row.anomaly_score || 0).toFixed(2)}</strong></td>
                <td style={{ fontSize: '0.76rem', color: '#cbd5e1' }}>
                  {(row.drivers || []).join(' • ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}