import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight } from 'lucide-react'
import StatCard from '../components/StatCard.jsx'
import LiveFireMap from '../maps/LiveFireMap.jsx'
import SensorComparisonChart from '../charts/SensorComparisonChart.jsx'
import AnomalyTimelineChart from '../charts/AnomalyTimelineChart.jsx'
import { pageProps, itemVariants } from '../components/motion.js'
import {
  StatRowSkeleton,
  PanelHeadSkeleton,
  AreaChartSkeleton,
  BarChartSkeleton,
} from '../components/skeletons.jsx'
import { fmtNum } from '../lib/format.js'

export default function OverviewPage({ summary, geojson, calendarDays, region, selectedDate, onNavigate, isLoading = false }) {
  const breakdown = summary?.match_breakdown || {}
  const regionLabel = region?.label || 'Global'

  return (
    <motion.div {...pageProps}>
      {isLoading ? (
        <StatRowSkeleton count={4} />
      ) : (
        <div className="grid-stats fade-in">
          <StatCard
            lead
            title="Harmonized detections"
            value={summary?.total_observations ?? 0}
            meta={`MODIS ${fmtNum(summary?.modis_count ?? 0)} · VIIRS ${fmtNum(summary?.viirs_count ?? 0)}`}
          />
          <StatCard
            title="Matched clusters"
            value={summary?.paired_clusters ?? 0}
            meta={`${fmtNum(breakdown['Matched'] ?? 0)} matched · ${fmtNum(breakdown['Possible Match'] ?? 0)} possible`}
          />
          <StatCard
            title="VIIRS-only fires"
            value={breakdown['VIIRS-only'] ?? 0}
            meta="Below the MODIS 1 km pixel"
          />
          <StatCard
            title="Peak radiative power"
            value={Number(summary?.max_frp_mw ?? 0)}
            decimals={1}
            unit="MW"
            meta={`Mean ${fmtNum(summary?.mean_frp_mw ?? 0, 1)} MW`}
          />
        </div>
      )}

      <motion.section variants={itemVariants} className="panel">
        {isLoading ? (
          <PanelHeadSkeleton titleWidth={160} subWidth={300} toolWidth={124} />
        ) : (
          <div className="panel-head fade-in">
            <div>
              <div className="panel-title">Spatial distribution</div>
              <div className="panel-sub">Harmonized MODIS and VIIRS hotspots across {regionLabel}</div>
            </div>
            <button type="button" className="btn-secondary" onClick={() => onNavigate('map')}>
              Map controls
              <ArrowUpRight size={16} strokeWidth={1.5} absoluteStrokeWidth />
            </button>
          </div>
        )}
        {/* Stays mounted so tiles load behind its own skeleton overlay */}
        <LiveFireMap geojson={geojson} selectedDate={selectedDate} region={region} loading={isLoading} />
      </motion.section>

      <div className="grid-lead">
        <motion.section variants={itemVariants} className="panel">
          {isLoading ? (
            <>
              <PanelHeadSkeleton titleWidth={200} subWidth={340} />
              <AreaChartSkeleton height={320} />
            </>
          ) : (
            <div className="fade-in">
              <div className="panel-head">
                <div>
                  <div className="panel-title">Fire radiative power · 30 days</div>
                  <div className="panel-sub">Daily total MW across {regionLabel}, ending {selectedDate || 'n/a'}</div>
                </div>
              </div>
              <AnomalyTimelineChart days={calendarDays} />
            </div>
          )}
        </motion.section>

        <motion.section variants={itemVariants} className="panel">
          {isLoading ? (
            <>
              <PanelHeadSkeleton titleWidth={140} subWidth={180} />
              <BarChartSkeleton height={320} />
            </>
          ) : (
            <div className="fade-in">
              <div className="panel-head">
                <div>
                  <div className="panel-title">Sensor gap · 30 days</div>
                  <div className="panel-sub">Daily detections by sensor</div>
                </div>
              </div>
              <SensorComparisonChart days={calendarDays} />
            </div>
          )}
        </motion.section>
      </div>
    </motion.div>
  )
}
