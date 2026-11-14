import React from 'react'
import { motion } from 'framer-motion'
import StatCard from '../components/StatCard.jsx'

export default function HarmonizationPage({ matches = [], summary }) {
  const breakdown = summary?.match_breakdown || {}

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <div className="grid-4">
        {Object.entries(breakdown).map(([status, count], idx) => (
          <StatCard
            key={status}
            hero={idx === 0}
            title={status}
            value={count}
            subtitle="Spatio-temporal classification"
          />
        ))}
      </div>

      <div className="bento-card">
        <div className="card-header">
          <div>
            <div className="card-title">Cross-Sensor Spatio-Temporal Pair Audit Log</div>
            <div className="card-sub">MODIS and VIIRS detections linked within ≤ 1.5 km spatial radius and ≤ 4 hours orbital overpass gap</div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Match ID</th>
                <th>Status</th>
                <th>Distance (km)</th>
                <th>Overpass Gap (min)</th>
                <th>MODIS FRP (MW)</th>
                <th>VIIRS FRP (MW)</th>
                <th>H3 Cell</th>
              </tr>
            </thead>
            <tbody>
              {matches.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ color: '#94a3b8' }}>No paired records found in sample.</td>
                </tr>
              ) : (
                matches.slice(0, 40).map((m, idx) => (
                  <tr key={m.match_id || idx}>
                    <td><code>{m.match_id || `PAIR-${idx + 1}`}</code></td>
                    <td>
                      <span className={`badge ${m.match_status === 'Matched' ? 'badge-matched' : 'badge-possible'}`}>
                        {m.match_status || 'Matched'}
                      </span>
                    </td>
                    <td>{Number(m.distance_km ?? m.nearest_dist_km ?? 0).toFixed(2)} km</td>
                    <td>{Math.round(Number(m.time_diff_min ?? 0))} min</td>
                    <td>{Number(m.modis_frp ?? 0).toFixed(1)}</td>
                    <td>{Number(m.viirs_frp ?? 0).toFixed(1)}</td>
                    <td><code>{m.h3_index || '—'}</code></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  )
}