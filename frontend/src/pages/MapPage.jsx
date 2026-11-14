import React from 'react'
import { motion } from 'framer-motion'
import LiveFireMap from '../maps/LiveFireMap.jsx'

export default function MapPage({ geojson, filters, onFilterChange, selectedDate }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 25 }}
      className="bento-card"
    >
      <div className="card-header">
        <div>
          <div className="card-title">Interactive MODIS–VIIRS Harmonized Map & NASA GIBS Overlay</div>
          <div className="card-sub">Filter by sensor family or cross-sensor matching status</div>
        </div>
        <div className="control-group">
          <select
            className="control-select"
            value={filters.sensor}
            onChange={(e) => onFilterChange({ ...filters, sensor: e.target.value })}
          >
            <option value="">All Sensors (MODIS + VIIRS)</option>
            <option value="MODIS">MODIS Only (1 km)</option>
            <option value="VIIRS">VIIRS Only (375 m)</option>
          </select>

          <select
            className="control-select"
            value={filters.match_status}
            onChange={(e) => onFilterChange({ ...filters, match_status: e.target.value })}
          >
            <option value="">All Match Statuses</option>
            <option value="Matched">Matched (Both Sensors)</option>
            <option value="Possible Match">Possible Match</option>
            <option value="VIIRS-only">VIIRS-only (Sub-pixel)</option>
            <option value="MODIS-only">MODIS-only</option>
          </select>
        </div>
      </div>

      <LiveFireMap geojson={geojson} selectedDate={selectedDate} />
    </motion.div>
  )
}