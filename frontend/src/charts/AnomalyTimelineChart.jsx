import React from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { SERIES, gridProps, axisProps, yAxisProps, tooltipProps } from './chartTheme.js'

export default function AnomalyTimelineChart({ days = [], height = 320 }) {
  const chartData = days.map((d) => ({
    date: (d.utc_date || d.date || '').slice(5),
    Total_FRP_MW: Number((d.total_frp_mw ?? d.total_frp ?? 0).toFixed(1)),
  }))

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="date" {...axisProps} minTickGap={24} />
          <YAxis {...yAxisProps} />
          <Tooltip {...tooltipProps} />
          <Area
            type="monotone"
            dataKey="Total_FRP_MW"
            name="FRP (MW)"
            stroke={SERIES.lead}
            strokeWidth={1.5}
            fill={SERIES.lead}
            fillOpacity={0.08}
            activeDot={{ r: 3, fill: SERIES.lead, stroke: 'var(--bg-2)', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
