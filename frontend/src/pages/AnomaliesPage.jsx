import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { fetchArchiveComparison, fetchArchiveAnomalies } from '../services/api.js'
import { pageProps, itemVariants } from '../components/motion.js'
import { fmtNum } from '../lib/format.js'
import { TableSkeletonRows } from '../components/skeletons.jsx'

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export default function AnomaliesPage({ region, selectedDate }) {
  const defaultYear = selectedDate ? Number(selectedDate.slice(0, 4)) : 2025
  const [compYear, setCompYear] = useState(defaultYear >= 2003 && defaultYear <= 2026 ? defaultYear : 2025)
  const [comparison, setComparison] = useState(null)
  const [h3Anomalies, setH3Anomalies] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    const bbox = region?.bbox || '-180,-90,180,90'
    Promise.all([
      fetchArchiveComparison(bbox, compYear).catch(() => null),
      fetchArchiveAnomalies(bbox, compYear, 60).catch(() => ({ items: [] })),
    ])
      .then(([compRes, anomRes]) => {
        if (!active) return
        setComparison(compRes)
        setH3Anomalies(anomRes?.items || [])
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [region?.bbox, compYear])

  const hasMonths = comparison?.months?.length > 0
  const monthsSkeleton = loading && !hasMonths
  const cellsSkeleton = loading && h3Anomalies.length === 0

  return (
    <motion.div {...pageProps}>
      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Baseline departure · {compYear}</div>
            <div className="panel-sub">
              {region?.label || 'Global'} detections vs the 2003–2026 median and p25–p75 band
            </div>
          </div>
          <div className="panel-tools">
            {loading && <span className="stat-meta">Loading</span>}
            <select
              className="control-select"
              value={compYear}
              onChange={(e) => setCompYear(Number(e.target.value))}
              aria-label="Comparison year"
            >
              {Array.from({ length: 24 }, (_, i) => 2026 - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        {hasMonths || monthsSkeleton ? (
          <div className={`table-wrap ${loading && hasMonths ? 'is-dimmed' : ''}`}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th className="num">{compYear} detections</th>
                  <th className="num">Median</th>
                  <th className="num">p25–p75</th>
                  <th className="num">Max</th>
                  <th className="num">vs median</th>
                </tr>
              </thead>
              <tbody key={monthsSkeleton ? 'skel' : 'data'} className={monthsSkeleton ? undefined : 'fade-in'}>
                {monthsSkeleton ? <TableSkeletonRows rows={8} cols={6} /> : comparison.months.map((m) => {
                  const pct = m.pct_vs_median
                  const isElevated = pct !== null && pct > 25
                  return (
                    <tr key={m.month}>
                      <td>{MONTH_NAMES[m.month - 1]}</td>
                      <td className="num">{fmtNum(m.total || 0)}</td>
                      <td className="num dim">{fmtNum(m.median_other_years || 0)}</td>
                      <td className="num dim">
                        {fmtNum(m.p25 || 0)}–{fmtNum(m.p75 || 0)}
                      </td>
                      <td className="num dim">{fmtNum(m.max_other_years || 0)}</td>
                      <td className={`num ${isElevated ? 'delta-up' : 'delta-flat'}`}>
                        {pct === null ? 'n/a' : `${pct >= 0 ? '+' : ''}${fmtNum(pct, 1)}%`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="panel-sub">No monthly baseline rows for {region?.label} in {compYear}.</div>
        )}
      </motion.section>

      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Isolation forest anomalies · {compYear}</div>
            <div className="panel-sub">
              Scored by <code>isolation_forest_archive_v1.joblib</code> against per-cell seasonal baselines
            </div>
          </div>
          <span className="stat-meta tnum" style={{ visibility: cellsSkeleton ? 'hidden' : undefined }}>{fmtNum(h3Anomalies.length)} cells</span>
        </div>

        <div className={`table-wrap ${loading && h3Anomalies.length > 0 ? 'is-dimmed' : ''}`}>
          <table className="data-table">
            <thead>
              <tr>
                <th>H3 cell · res 5</th>
                <th>Month</th>
                <th className="num">Lat, lon</th>
                <th>Class</th>
                <th className="num">MODIS / VIIRS</th>
                <th className="num">Peak FRP MW</th>
                <th className="num">Score</th>
                <th>Drivers</th>
              </tr>
            </thead>
            <tbody key={cellsSkeleton ? 'skel' : 'data'} className={cellsSkeleton ? undefined : 'fade-in'}>
              {cellsSkeleton ? (
                <TableSkeletonRows rows={8} cols={8} />
              ) : h3Anomalies.length === 0 ? (
                <tr className="empty-row">
                  <td colSpan="8">No scored H3 cells for this filter.</td>
                </tr>
              ) : (
                h3Anomalies.map((row, idx) => (
                  <tr key={`${row.h3_index}-${row.utc_date}-${idx}`}>
                    <td><code>{row.h3_index}</code></td>
                    <td className="dim">{row.utc_date}</td>
                    <td className="num dim">
                      {row.latitude}, {row.longitude}
                    </td>
                    <td>
                      <span className={`status ${row.is_anomaly ? 'status-anomaly' : 'status-normal'}`}>
                        {row.baseline_label}
                      </span>
                    </td>
                    <td className="num">
                      {fmtNum(row.modis_count)} / {fmtNum(row.viirs_count)}
                    </td>
                    <td className="num">{fmtNum(row.max_frp, 1)}</td>
                    <td className="num">{row.anomaly_score}</td>
                    <td className="wrap">{(row.drivers || []).join(' · ')}</td>
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
