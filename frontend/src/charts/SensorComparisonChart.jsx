import React from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts'

export default function SensorComparisonChart({ days = [] }) {
  const chartData = days.map((d) => ({
    date: (d.utc_date || d.date || '').slice(5),
    MODIS_1km: d.modis_count ?? 0,
    VIIRS_375m: d.viirs_count ?? 0,
    Matched_Clusters: d.matched_count ?? d.matched_group_count ?? 0,
  }))

  return (
    <div style={{ width: '100%', height: 290 }}>
      <ResponsiveContainer>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
          <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} />
          <Tooltip contentStyle={{ background: '#090e1c', border: '1px solid rgba(255,94,58,0.35)', borderRadius: 10, color: '#f8fafc' }} />
          <Legend />
          <Bar dataKey="MODIS_1km" name="MODIS (1 km)" fill="#3b82f6" radius={[5, 5, 0, 0]} />
          <Bar dataKey="VIIRS_375m" name="VIIRS (375 m)" fill="#ff5e3a" radius={[5, 5, 0, 0]} />
          <Bar dataKey="Matched_Clusters" name="Matched Events" fill="#10b981" radius={[5, 5, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}