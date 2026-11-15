import React from 'react'
import { motion } from 'framer-motion'

export default function DataExplorerPage({ geojson }) {
  const features = geojson?.features || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12, transition: { duration: 0.18 } }}
      transition={{ type: 'spring', stiffness: 320, damping: 25 }}
      className="bento-card"
    >
      <div className="card-header">
        <div>
          <div className="card-title">Harmonized GeoJSON Record Explorer ({features.length} records)</div>
          <div className="card-sub">Unified schema combining NASA FIRMS MODIS and VIIRS observations</div>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source ID</th>
              <th>Sensor</th>
              <th>UTC Datetime</th>
              <th>Lat, Lon</th>
              <th>FRP (MW)</th>
              <th>Confidence</th>
              <th>Match Status</th>
              <th>H3 Index</th>
            </tr>
          </thead>
          <tbody>
            {features.slice(0, 50).map((f, idx) => {
              const p = f.properties
              const [lon, lat] = f.geometry.coordinates
              return (
                <tr key={`${p.source_id}-${idx}`}>
                  <td><code>{p.source_id}</code></td>
                  <td>
                    <span className={`badge ${p.sensor_family === 'MODIS' ? 'badge-modis' : 'badge-viirs'}`}>
                      {p.sensor_family}
                    </span>
                  </td>
                  <td>{p.acq_datetime}</td>
                  <td>{lat.toFixed(4)}, {lon.toFixed(4)}</td>
                  <td>{p.frp.toFixed(2)}</td>
                  <td>{p.confidence_tier}</td>
                  <td>{p.match_status}</td>
                  <td><code>{p.h3_index}</code></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}