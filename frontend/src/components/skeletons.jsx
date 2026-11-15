import React from 'react'
import { motion } from 'framer-motion'
import Skeleton from './Skeleton.jsx'
import { itemVariants } from './motion.js'

// Layout-matched placeholders built from <Skeleton />. Every box reserves the
// real element's line height so nothing shifts when data replaces it.

const Line = ({ lineHeight, ...rest }) => (
  <div className="skel-line" style={{ height: lineHeight }}>
    <Skeleton {...rest} />
  </div>
)

/** Mirrors StatCard: 20px label line, 32px figure, 16px meta line. */
export function StatCardSkeleton() {
  return (
    <motion.div variants={itemVariants} className="panel stat-card" aria-hidden="true">
      <Line lineHeight={20} width="55%" height={10} />
      <Line lineHeight={40} width="45%" height={28} />
      <Line lineHeight={16} width="70%" height={8} />
    </motion.div>
  )
}

export function StatRowSkeleton({ count = 4 }) {
  return (
    <div className="grid-stats" aria-busy="true">
      {Array.from({ length: count }, (_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  )
}

/** Mirrors .panel-head: 20px mono title, 2px gap, 20px subtitle, optional 32px tool. */
export function PanelHeadSkeleton({ titleWidth = 180, subWidth = 320, toolWidth }) {
  return (
    <div className="panel-head" aria-hidden="true">
      <div style={{ flex: 1, minWidth: 0 }}>
        <Line lineHeight={20} width={titleWidth} height={10} style={{ maxWidth: '100%' }} />
        <Line lineHeight={20} width={subWidth} height={8} style={{ maxWidth: '100%', marginTop: 2 }} />
      </div>
      {toolWidth ? <Skeleton width={toolWidth} height={32} radius="var(--r-ctl)" /> : null}
    </div>
  )
}

/** Area/line chart: y labels, faint grid lines over a shimmering plot, x labels. */
export function AreaChartSkeleton({ height = 320 }) {
  const rows = 5
  return (
    <div className="chart-skel" style={{ height }} aria-hidden="true">
      <div className="chart-skel-y">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} width={28} height={8} style={{ marginLeft: 'auto' }} />
        ))}
      </div>
      <div className="chart-skel-plot">
        <Skeleton
          width="100%"
          height="100%"
          style={{ position: 'absolute', inset: 0, opacity: 0.55 }}
        />
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="chart-skel-grid" style={{ position: 'relative' }} />
        ))}
      </div>
      <div className="chart-skel-x">
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton key={i} width={32} height={8} />
        ))}
      </div>
    </div>
  )
}

const BAR_HEIGHTS = [38, 72, 64, 58, 84, 52, 46, 30, 66, 78, 40, 56, 70, 44]

/** Bar chart: legend row (16px + 12px gap) then bars of varying heights. */
export function BarChartSkeleton({ height = 320 }) {
  return (
    <div aria-hidden="true">
      <div className="legend" style={{ marginBottom: 12, height: 16 }}>
        <Skeleton width={80} height={8} />
        <Skeleton width={72} height={8} />
      </div>
      <div className="chart-skel" style={{ height: height - 28 }}>
        <div className="chart-skel-y">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} width={24} height={8} style={{ marginLeft: 'auto' }} />
          ))}
        </div>
        <div className="chart-skel-plot">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="chart-skel-grid" />
          ))}
          <div className="chart-skel-bars">
            {BAR_HEIGHTS.map((h, i) => (
              <Skeleton key={i} height={`${h}%`} width="auto" />
            ))}
          </div>
        </div>
        <div className="chart-skel-x">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} width={32} height={8} />
          ))}
        </div>
      </div>
    </div>
  )
}

const CELL_WIDTHS = ['72%', '48%', '60%', '36%', '80%', '54%', '42%', '66%']

/** <tbody> rows at the real 40px row height. */
export function TableSkeletonRows({ rows = 8, cols = 6 }) {
  return Array.from({ length: rows }, (_, r) => (
    <tr key={`skel-${r}`} aria-hidden="true">
      {Array.from({ length: cols }, (_, c) => (
        <td key={c}>
          <Skeleton width={CELL_WIDTHS[(r + c * 3) % CELL_WIDTHS.length]} height={10} style={{ minWidth: 24 }} />
        </td>
      ))}
    </tr>
  ))
}

/** 30-day calendar cells: date, count, FRP lines at real line heights. */
export function CalendarGridSkeleton({ days = 30 }) {
  return (
    <div className="calendar-grid" aria-hidden="true">
      {Array.from({ length: days }, (_, i) => (
        <div key={i} className="calendar-cell" style={{ cursor: 'default' }}>
          <Line lineHeight={16} width="40%" height={8} />
          <Line lineHeight={24} width="55%" height={14} />
          <Line lineHeight={16} width="65%" height={8} />
        </div>
      ))}
    </div>
  )
}
