import React, { useState } from 'react'
import DayDetailDrawer from './DayDetailDrawer.jsx'
import { fmtNum } from '../lib/format.js'

export const dayCount = (d) => d.total_detections ?? d.count ?? d.total_count ?? 0

export default function BurningCalendar({ days = [] }) {
  const [selectedDay, setSelectedDay] = useState(null)

  if (!days.length) {
    return <div className="panel-sub">No days available in the current window.</div>
  }

  const maxCount = Math.max(...days.map(dayCount), 1)

  return (
    <div>
      <div className="calendar-grid">
        {days.map((day, idx) => {
          const key = day.utc_date || day.date || idx
          const count = dayCount(day)
          const intensity = Math.min(1, Math.sqrt(count / maxCount))
          const isSelected = selectedDay && (selectedDay.utc_date || selectedDay.date) === (day.utc_date || day.date)

          return (
            <button
              key={key}
              type="button"
              className="calendar-cell"
              aria-pressed={!!isSelected}
              onClick={() => setSelectedDay(isSelected ? null : day)}
              style={
                count > 0
                  ? { background: `color-mix(in srgb, var(--heat) ${Math.round(4 + intensity * 20)}%, var(--bg-3))` }
                  : undefined
              }
            >
              <span className="cc-date">{(day.utc_date || day.date || '').slice(5)}</span>
              <span className="cc-count">{fmtNum(count)}</span>
              <span className="cc-frp">{fmtNum(day.total_frp_mw ?? day.total_frp ?? 0)} MW</span>
            </button>
          )
        })}
      </div>

      <DayDetailDrawer day={selectedDay} onClose={() => setSelectedDay(null)} />
    </div>
  )
}
