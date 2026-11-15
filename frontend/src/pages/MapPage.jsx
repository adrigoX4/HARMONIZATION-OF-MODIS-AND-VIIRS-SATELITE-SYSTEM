import React from 'react'
import { motion } from 'framer-motion'
import { Radio } from 'lucide-react'
import LiveFireMap from '../maps/LiveFireMap.jsx'
import { pageProps, itemVariants } from '../components/motion.js'

export default function MapPage({ geojson, filters, onFilterChange, selectedDate, region, isLiveMode, onToggleLive, isLoading = false }) {
  return (
    <motion.div {...pageProps}>
      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">
              {isLiveMode ? 'Live detections · last 24 h' : `Archive detections · ${selectedDate || 'n/a'}`}
            </div>
            <div className="panel-sub">
              {isLiveMode
                ? 'Streaming MODIS_NRT, VIIRS_SNPP_NRT and VIIRS_NOAA20_NRT from NASA FIRMS'
                : `Archive detections for ${region?.label}. Turn on Live NRT for the real-time feed`}
            </div>
          </div>
          <div className="panel-tools">
            <button
              type="button"
              className="btn-secondary"
              aria-pressed={isLiveMode}
              onClick={() => onToggleLive(!isLiveMode)}
            >
              {isLiveMode ? <span className="status-dot live" /> : <Radio size={16} strokeWidth={1.5} absoluteStrokeWidth />}
              {isLiveMode ? 'Live stream on' : 'Live stream'}
            </button>

            <select
              className="control-select"
              value={filters.sensor}
              onChange={(e) => onFilterChange({ ...filters, sensor: e.target.value })}
              aria-label="Sensor"
            >
              <option value="">MODIS and VIIRS</option>
              <option value="MODIS">MODIS only · 1 km</option>
              <option value="VIIRS">VIIRS only · 375 m</option>
            </select>

            <select
              className="control-select"
              value={filters.match_status}
              onChange={(e) => onFilterChange({ ...filters, match_status: e.target.value })}
              aria-label="Match status"
            >
              <option value="">All match statuses</option>
              <option value="Matched">Matched · both sensors</option>
              <option value="Possible Match">Possible match</option>
              <option value="VIIRS-only">VIIRS-only · sub-pixel</option>
              <option value="MODIS-only">MODIS-only</option>
            </select>
          </div>
        </div>

        <LiveFireMap geojson={geojson} selectedDate={selectedDate} region={region} height={640} loading={isLoading} />
      </motion.section>
    </motion.div>
  )
}
