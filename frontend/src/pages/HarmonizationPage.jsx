import React from 'react'
import { motion } from 'framer-motion'
import StatCard from '../components/StatCard.jsx'
import { pageProps, itemVariants } from '../components/motion.js'
import { fmtNum } from '../lib/format.js'
import { StatRowSkeleton, TableSkeletonRows } from '../components/skeletons.jsx'
import Skeleton from '../components/Skeleton.jsx'

const STATUS_CLASS = {
  Matched: 'status-matched',
  'Possible Match': 'status-possible',
  'MODIS-only': 'status-modis',
  'VIIRS-only': 'status-viirs',
}

export default function HarmonizationPage({ matches = [], summary, region, selectedDate, isLiveMode, isLoading = false }) {
  const breakdown = summary?.match_breakdown || {}
  const when = isLiveMode ? 'last 24 h' : selectedDate

  return (
    <motion.div {...pageProps}>
      {isLoading ? (
        <StatRowSkeleton count={4} />
      ) : (
      <div className="grid-stats fade-in">
        {Object.entries(breakdown).map(([status, count], idx) => (
          <StatCard
            key={status}
            lead={idx === 0}
            title={status}
            value={Number(count) || 0}
            meta={`${region?.label || 'Global'} · ${when}`}
          />
        ))}
      </div>
      )}

      <motion.section variants={itemVariants} className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">Pair audit log · {when}</div>
            <div className="panel-sub">
              MODIS 1 km and VIIRS 375 m detections linked within a 1.5 km radius and a 4 h overpass gap
            </div>
          </div>
          {isLoading ? (
            <Skeleton width={96} height={8} style={{ marginTop: 6 }} />
          ) : (
            <span className="stat-meta tnum">{fmtNum(Math.min(matches.length, 60))} of {fmtNum(summary?.paired_clusters ?? matches.length)} pairs</span>
          )}
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Match ID</th>
                <th>Status</th>
                <th className="num">Lat, lon</th>
                <th className="num">Distance km</th>
                <th className="num">Gap min</th>
                <th className="num">MODIS FRP MW</th>
                <th className="num">VIIRS FRP MW</th>
                <th>H3 cell</th>
              </tr>
            </thead>
            <tbody className={isLoading ? undefined : 'fade-in'} key={isLoading ? 'skel' : 'data'}>
              {isLoading ? (
                <TableSkeletonRows rows={8} cols={8} />
              ) : matches.length === 0 ? (
                <tr className="empty-row">
                  <td colSpan="8">
                    No MODIS–VIIRS pairs for {region?.label} on {selectedDate}. Try Global Planetary or a peak fire date.
                  </td>
                </tr>
              ) : (
                matches.slice(0, 60).map((m, idx) => (
                  <tr key={m.match_id || idx}>
                    <td><code>{m.match_id || `PAIR-${idx + 1}`}</code></td>
                    <td>
                      <span className={`status ${STATUS_CLASS[m.match_status] || 'status-matched'}`}>
                        {m.match_status || 'Matched'}
                      </span>
                    </td>
                    <td className="num dim">
                      {fmtNum(m.latitude ?? 0, 3)}, {fmtNum(m.longitude ?? 0, 3)}
                    </td>
                    <td className="num">{fmtNum(m.distance_km ?? 0, 2)}</td>
                    <td className="num">{fmtNum(Math.round(Number(m.time_diff_min ?? 0)))}</td>
                    <td className="num">{fmtNum(m.modis_frp ?? 0, 1)}</td>
                    <td className="num">{fmtNum(m.viirs_frp ?? 0, 1)}</td>
                    <td><code>{m.h3_index || 'n/a'}</code></td>
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
