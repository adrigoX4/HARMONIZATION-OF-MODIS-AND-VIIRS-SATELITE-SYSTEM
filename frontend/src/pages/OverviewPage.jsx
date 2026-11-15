import React from 'react'
import { motion } from 'framer-motion'
import { Flame, GitMerge, Eye, Zap } from 'lucide-react'
import StatCard, { cardVariants } from '../components/StatCard.jsx'
import LiveFireMap from '../maps/LiveFireMap.jsx'
import SensorComparisonChart from '../charts/SensorComparisonChart.jsx'
import AnomalyTimelineChart from '../charts/AnomalyTimelineChart.jsx'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.065 },
  },
  exit: { opacity: 0, y: -12, transition: { duration: 0.18 } },
}

export default function OverviewPage({ summary, geojson, calendarDays, onNavigate }) {
  const breakdown = summary?.match_breakdown || {}

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="visible" exit="exit">
      <div className="grid-4">
        <StatCard
          hero
          icon={Flame}
          title="Total Harmonized Detections"
          value={summary?.total_observations ?? '—'}
          subtitle={`MODIS 1km: ${summary?.modis_count ?? 0} • VIIRS 375m: ${summary?.viirs_count ?? 0}`}
        />
        <StatCard
          icon={GitMerge}
          title="Cross-Sensor Matched Clusters"
          value={summary?.paired_clusters ?? '—'}
          subtitle={`Matched: ${breakdown['Matched'] ?? 0} • Possible: ${breakdown['Possible Match'] ?? 0}`}
          badge={<span className="badge badge-matched">≤ 1.5 km • ≤ 4h</span>}
        />
        <StatCard
          icon={Eye}
          title="Sub-Pixel VIIRS-Only Fires"
          value={breakdown['VIIRS-only'] ?? 0}
          subtitle="Small fires missed by 1 km MODIS pixels"
        />
        <StatCard
          icon={Zap}
          title="Peak Fire Radiative Power"
          value={`${summary?.max_frp_mw ?? 0} MW`}
          subtitle={`Mean intensity: ${summary?.mean_frp_mw ?? 0} MW`}
        />
      </div>

      <motion.div variants={cardVariants} className="bento-card" style={{ marginBottom: '1.35rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">Harmonized MODIS + VIIRS Spatial Distribution</div>
            <div className="card-sub">Click any thermal hotspot to inspect orbital overpass time delta, distance link, and H3 Res-5 cell</div>
          </div>
          <button className="btn-secondary" onClick={() => onNavigate('map')}>
            Open Full Map Controls →
          </button>
        </div>
        <LiveFireMap geojson={geojson} selectedDate={summary?.date_range?.end} />
      </motion.div>

      <div className="grid-2">
        <motion.div variants={cardVariants} className="bento-card">
          <div className="card-header">
            <div>
              <div className="card-title">Sensor Resolution Gap (MODIS 1 km vs VIIRS 375 m)</div>
              <div className="card-sub">Daily raw counts vs. spatio-temporally harmonized clusters</div>
            </div>
          </div>
          <SensorComparisonChart days={calendarDays} />
        </motion.div>

        <motion.div variants={cardVariants} className="bento-card">
          <div className="card-header">
            <div>
              <div className="card-title">Daily Fire Radiative Power (MW) Trajectory</div>
              <div className="card-sub">Radiant energy curve across the active window</div>
            </div>
          </div>
          <AnomalyTimelineChart days={calendarDays} />
        </motion.div>
      </div>
    </motion.div>
  )
}