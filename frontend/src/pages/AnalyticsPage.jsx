import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import SensorComparisonChart from '../charts/SensorComparisonChart.jsx'
import AnomalyTimelineChart from '../charts/AnomalyTimelineChart.jsx'
import { fetchArchiveSensorEra } from '../services/api.js'
import { pageProps, itemVariants } from '../components/motion.js'
import { fmtNum } from '../lib/format.js'
import { PanelHeadSkeleton, AreaChartSkeleton, BarChartSkeleton, TableSkeletonRows } from '../components/skeletons.jsx'

export default function AnalyticsPage({ calendarDays = [], region, isLoading = false }) {
  const [sensorEra, setSensorEra] = useState([])
  const [eraLoading, setEraLoading] = useState(false)

  useEffect(() => {
    let active = true
    setEraLoading(true)
    fetchArchiveSensorEra(region?.bbox || '-180,-90,180,90')
      .then((res) => {
        if (active) setSensorEra(res?.years || [])
      })
      .catch(() => {
        if (active) setSensorEra([])
      })
      .finally(() => {
        if (active) setEraLoading(false)
      })
    return () => {
      active = false
    }
  }, [region?.bbox])

  // Pivot sensorEra by year
  const byYear = {}
  sensorEra.forEach((r) => {
    if (!byYear[r.year]) byYear[r.year] = { year: r.year, MODIS: 0, SNPP: 0, NOAA20: 0, NOAA21: 0 }
    if (r.source_id.includes('MODIS')) byYear[r.year].MODIS += r.detections
    else if (r.source_id.includes('SNPP')) byYear[r.year].SNPP += r.detections
    else if (r.source_id.includes('NOAA20')) byYear[r.year].NOAA20 += r.detections
    else if (r.source_id.includes('NOAA21')) byYear[r.year].NOAA21 += r.detections
  })
  const eraRows = Object.values(byYear).sort((a, b) => b.year - a.year)
  const eraSkeleton = eraLoading && eraRows.length === 0

  return (
    <motion.div {...pageProps}>
      <div className="grid-lead">
        <motion.section variants={itemVariants} className="panel">
          {isLoading ? (
            <>
              <PanelHeadSkeleton titleWidth={200} subWidth={360} />
              <BarChartSkeleton height={320} />
            </>
          ) : (
          <div className="fade-in">
          <div className="panel-head">
            <div>
              <div className="panel-title">Detection counts by sensor</div>
              <div className="panel-sub">Why raw VIIRS 375 m counts exceed MODIS 1 km before calibration</div>
            </div>
          </div>
          <SensorComparisonChart days={calendarDays} />
          </div>
          )}
        </motion.section>

        <motion.section variants={itemVariants} className="panel">
          {isLoading ? (
            <>
              <PanelHeadSkeleton titleWidth={160} subWidth={300} />
              <AreaChartSkeleton height={320} />
            </>
          ) : (
          <div className="fade-in">
          <div className="panel-head">
            <div>
              <div className="panel-title">Fire radiative power</div>
              <div className="panel-sub">Energy totals stay stable across sensor resolutions</div>
            </div>
          </div>
          <AnomalyTimelineChart days={calendarDays} />
          </div>
          )}
        </motion.section>
      </div>

      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Sensor era log · 2003–2026</div>
            <div className="panel-sub">
              Annual detections across Terra/Aqua MODIS, Suomi NPP, NOAA-20 and NOAA-21 for {region?.label}
            </div>
          </div>
        </div>
        <div className={`table-wrap ${eraLoading && eraRows.length > 0 ? 'is-dimmed' : ''}`}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Year</th>
                <th className="num">MODIS · 1 km</th>
                <th className="num">VIIRS S-NPP · 375 m</th>
                <th className="num">VIIRS NOAA-20 · 375 m</th>
                <th className="num">VIIRS NOAA-21 · 375 m</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody key={eraSkeleton ? 'skel' : 'data'} className={eraSkeleton ? undefined : 'fade-in'}>
              {eraSkeleton ? (
                <TableSkeletonRows rows={8} cols={6} />
              ) : eraRows.length === 0 ? (
                <tr className="empty-row">
                  <td colSpan="6">No sensor era rows for this region.</td>
                </tr>
              ) : (
                eraRows.map((r) => (
                  <tr key={r.year}>
                    <td className="mono">{r.year}</td>
                    <td className="num dim">{fmtNum(r.MODIS)}</td>
                    <td className="num dim">{fmtNum(r.SNPP)}</td>
                    <td className="num dim">{fmtNum(r.NOAA20)}</td>
                    <td className="num dim">{fmtNum(r.NOAA21)}</td>
                    <td className="num">{fmtNum(r.MODIS + r.SNPP + r.NOAA20 + r.NOAA21)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.section>
    </motion.div>
  )
}
