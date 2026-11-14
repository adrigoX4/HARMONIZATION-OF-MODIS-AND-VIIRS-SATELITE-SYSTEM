import React from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

export default function AnomalyTimelineChart({ days = [] }) {
  const chartData = days.map((d) => ({
    date: (d.utc_date || d.date || '').slice(5),
    Total_FRP_MW: Number((d.total_frp_mw ?? d.total_frp ?? 0).toFixed(1)),
  }))

  return (
    <div style={{ width: '100%', height: 290 }}>
      <ResponsiveContainer>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="frpGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff5e3a" stopOpacity={0.65} />
              <stop offset="95%" stopColor="#ff5e3a" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
          <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} />
          <Tooltip contentStyle={{ background: '#090e1c', border: '1px solid rgba(255,94,58,0.35)', borderRadius: 10, color: '#f8fafc' }} />
          <Area type="monotone" dataKey="Total_FRP_MW" name="Radiative Power (MW)" stroke="#ff5e3a" strokeWidth={2.5} fill="url(#frpGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}