import React from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { SERIES, gridProps, axisProps, yAxisProps, tooltipProps } from './chartTheme.js'

const KEYS = [
  { key: 'VIIRS_375m', label: 'VIIRS 375 m', color: SERIES.viirs },
  { key: 'MODIS_1km', label: 'MODIS 1 km', color: SERIES.modis },
  { key: 'Matched_Clusters', label: 'Matched', color: SERIES.matched },
]

export default function SensorComparisonChart({ days = [], height = 320 }) {
  const chartData = days.map((d) => ({
    date: (d.utc_date || d.date || '').slice(5),
    MODIS_1km: d.modis_count ?? 0,
    VIIRS_375m: d.viirs_count ?? 0,
    Matched_Clusters: d.matched_count ?? d.matched_group_count ?? 0,
  }))
  const hasMatched = chartData.some((d) => d.Matched_Clusters > 0)
  const keys = KEYS.filter((k) => k.key !== 'Matched_Clusters' || hasMatched)

  return (
    <div>
      <div className="legend" style={{ marginBottom: 12 }}>
        {keys.map((k) => (
          <span key={k.key} className="legend-item">
            <span className="legend-swatch" style={{ background: k.color }} />
            {k.label}
          </span>
        ))}
      </div>
      <div style={{ width: '100%', height: height - 28 }}>
        <ResponsiveContainer>
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barGap={1} barCategoryGap="24%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="date" {...axisProps} minTickGap={24} />
            <YAxis {...yAxisProps} />
            <Tooltip {...tooltipProps} />
            {keys.map((k) => (
              <Bar
                key={k.key}
                dataKey={k.key}
                name={k.label}
                fill={k.color}
                radius={[2, 2, 0, 0]}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
