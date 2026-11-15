import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import BurningCalendar from '../calendar/BurningCalendar.jsx'
import { fetchArchiveCalendar } from '../services/api.js'
import { pageProps, itemVariants } from '../components/motion.js'
import { fmtNum, fmtCompact } from '../lib/format.js'
import { PanelHeadSkeleton, CalendarGridSkeleton } from '../components/skeletons.jsx'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Single-hue ramp from the --heat token (cyan in dark, coral in light), five steps;
// sqrt scale so quiet months still register.
const RAMP = [0.14, 0.3, 0.48, 0.7, 1]
const EMPTY = 'var(--heat-empty)'
const heat = (a) => `color-mix(in srgb, var(--heat) ${Math.round(a * 100)}%, var(--heat-empty))`

function cellStyle(value, maxVal) {
  if (!value || maxVal <= 0) return { background: EMPTY, color: 'var(--text-3)' }
  const ratio = Math.min(1, Math.sqrt(value / maxVal))
  const step = Math.min(RAMP.length - 1, Math.floor(ratio * RAMP.length))
  const alpha = RAMP[step]
  return {
    background: heat(alpha),
    color: alpha >= 0.7 ? 'var(--heat-ink-high)' : 'var(--heat-ink-low)',
  }
}

export default function CalendarPage({ days = [], region, isLoading = false }) {
  const [matrixCells, setMatrixCells] = useState([])
  const [metric, setMetric] = useState('total')
  const [loadingArchive, setLoadingArchive] = useState(false)

  useEffect(() => {
    let active = true
    setLoadingArchive(true)
    fetchArchiveCalendar(region?.bbox || '-180,-90,180,90', 2003, 2026)
      .then((res) => {
        if (active) setMatrixCells(res?.cells || [])
      })
      .catch(() => {
        if (active) setMatrixCells([])
      })
      .finally(() => {
        if (active) setLoadingArchive(false)
      })
    return () => {
      active = false
    }
  }, [region?.bbox])

  const heatSkeleton = loadingArchive && matrixCells.length === 0
  const heatDimmed = loadingArchive && matrixCells.length > 0

  const years = Array.from({ length: 24 }, (_, i) => 2003 + i)
  const cellMap = new Map()
  let maxVal = 0
  matrixCells.forEach((c) => {
    const val = Number(c[metric] || 0)
    if (val > maxVal) maxVal = val
    cellMap.set(`${c.year}-${c.month}`, c)
  })

  return (
    <motion.div {...pageProps}>
      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Monthly activity · 2003–2026</div>
            <div className="panel-sub">
              24-year seasonal fire regime for {region?.label || 'Global'}. Change the region in the header
            </div>
          </div>
          <select
            className="control-select"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            aria-label="Calendar metric"
          >
            <option value="total">Total detections</option>
            <option value="frp_sum_mw">Total radiative power (MW)</option>
            <option value="modis">MODIS detections · 1 km</option>
            <option value="viirs">VIIRS detections · 375 m</option>
          </select>
        </div>

        <div className="legend" style={{ marginBottom: 12 }}>
          <span className="legend-item">
            Less
            <span className="legend-ramp">
              <span style={{ background: EMPTY }} />
              {RAMP.map((a) => (
                <span key={a} style={{ background: heat(a) }} />
              ))}
            </span>
            More
          </span>
          <span className="push tnum">
            {loadingArchive ? 'Querying DuckDB' : `Peak ${fmtNum(Math.round(maxVal))}`}
          </span>
        </div>

        <div style={{ overflowX: 'auto' }} className={heatDimmed ? 'is-dimmed' : undefined}>
          <table className="heatmap">
            <thead>
              <tr>
                <th>Year</th>
                {MONTHS.map((m) => (
                  <th key={m}>{m}</th>
                ))}
              </tr>
            </thead>
            <tbody key={heatSkeleton ? 'skel' : 'data'} className={heatSkeleton ? undefined : 'fade-in'} aria-busy={heatSkeleton}>
              {years.map((yr) => (
                <tr key={yr}>
                  <td className="hm-year">{yr}</td>
                  {MONTHS.map((_, idx) => {
                    const m = idx + 1
                    const rec = cellMap.get(`${yr}-${m}`)
                    const val = rec ? Number(rec[metric] || 0) : 0
                    if (heatSkeleton) return <td key={m} className="hm-cell skeleton" />
                    const label = `${yr}-${String(m).padStart(2, '0')}`
                    return (
                      <td
                        key={m}
                        className="hm-cell"
                        style={cellStyle(val, maxVal)}
                        title={
                          rec
                            ? `${label}: ${fmtNum(rec.total || 0)} detections · ${fmtNum(Math.round(rec.frp_sum_mw || 0))} MW`
                            : `${label}: 0 detections`
                        }
                      >
                        {val > 0 ? fmtCompact(val) : ''}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      <motion.section variants={itemVariants} className="panel">
        {isLoading ? (
          <>
            <PanelHeadSkeleton titleWidth={120} subWidth={340} />
            <CalendarGridSkeleton days={30} />
          </>
        ) : (
        <div className="fade-in">
        <div className="panel-head">
          <div>
            <div className="panel-title">30-day window</div>
            <div className="panel-sub">Daily detections and radiative power ending on the selected date</div>
          </div>
        </div>
        <BurningCalendar days={days} />
        </div>
        )}
      </motion.section>
    </motion.div>
  )
}
