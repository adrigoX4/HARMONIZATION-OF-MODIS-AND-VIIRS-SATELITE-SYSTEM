import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { fetchArchiveHotspots, getArchiveCsvUrl } from '../services/api.js'
import { pageProps, itemVariants } from '../components/motion.js'
import { fmtNum } from '../lib/format.js'
import { TableSkeletonRows } from '../components/skeletons.jsx'

export default function DataExplorerPage({ region, selectedDate, sensorFilter }) {
  const targetDate = selectedDate || '2026-09-15'
  const [startDate, setStartDate] = useState(targetDate)
  const [endDate, setEndDate] = useState(targetDate)
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (selectedDate) {
      setStartDate(selectedDate)
      setEndDate(selectedDate)
    }
  }, [selectedDate])

  useEffect(() => {
    let active = true
    setLoading(true)
    fetchArchiveHotspots({
      bbox: region?.bbox || '-180,-90,180,90',
      start: startDate,
      end: endDate,
      sensor: sensorFilter || undefined,
      limit: 200,
    })
      .then((res) => {
        if (active) setRecords(res?.records || [])
      })
      .catch(() => {
        if (active) setRecords([])
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [region?.bbox, startDate, endDate, sensorFilter])

  const csvDownloadUrl = getArchiveCsvUrl({
    bbox: region?.bbox || '-180,-90,180,90',
    start: startDate,
    end: endDate,
    sensor: sensorFilter || undefined,
    limit: 200000,
  })

  return (
    <motion.div {...pageProps}>
      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Hotspot archive</div>
            <div className="panel-sub">
              {region?.label || 'Global'} · 21.98M records in DuckDB Parquet · {loading ? 'Querying' : `${fmtNum(records.length)} preview rows`}
            </div>
          </div>

          <div className="panel-tools">
            <input
              type="date"
              className="control-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              aria-label="Start date"
            />
            <span className="stat-meta">to</span>
            <input
              type="date"
              className="control-input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              aria-label="End date"
            />
            <a href={csvDownloadUrl} className="btn-primary">
              <Download size={16} strokeWidth={1.5} absoluteStrokeWidth />
              Export CSV
            </a>
          </div>
        </div>

        <div className={`table-wrap ${loading && records.length > 0 ? 'is-dimmed' : ''}`}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Sensor</th>
                <th>Instrument</th>
                <th>UTC</th>
                <th className="num">Lat, lon</th>
                <th className="num">FRP MW</th>
                <th>Confidence</th>
                <th>Day/night</th>
                <th>H3 cell · res 5</th>
              </tr>
            </thead>
            <tbody key={loading && records.length === 0 ? 'skel' : 'data'} className={loading && records.length === 0 ? undefined : 'fade-in'}>
              {loading && records.length === 0 ? (
                <TableSkeletonRows rows={8} cols={9} />
              ) : records.length === 0 ? (
                <tr className="empty-row">
                  <td colSpan="9">
                    No detections in this date range and region.
                  </td>
                </tr>
              ) : (
                records.map((r) => (
                  <tr key={r.id}>
                    <td><code>{r.id}</code></td>
                    <td>
                      <span className={`status ${r.sensor_family === 'MODIS' ? 'status-modis' : 'status-viirs'}`}>
                        {r.sensor_family}
                      </span>
                    </td>
                    <td className="dim">{r.instrument}</td>
                    <td className="mono dim">{r.acq_datetime}</td>
                    <td className="num dim">
                      {r.latitude}, {r.longitude}
                    </td>
                    <td className="num">{fmtNum(r.frp, 2)}</td>
                    <td className="dim">{r.confidence_tier}</td>
                    <td className="dim">{r.daynight}</td>
                    <td><code>{r.h3_index}</code></td>
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
