import React from 'react'

export default function HotspotPopup({ props }) {
  return (
    <div style={{ minWidth: '225px', color: '#0f172a', fontSize: '0.82rem', lineHeight: 1.45 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <strong>{props.sensor_family} ({props.spatial_res_m}m)</strong>
        <span
          style={{
            background: props.match_status === 'Matched' ? '#dcfce7' : '#ffedd5',
            color: props.match_status === 'Matched' ? '#166534' : '#9a3412',
            padding: '2px 8px',
            borderRadius: '999px',
            fontSize: '0.72rem',
            fontWeight: 700,
          }}
        >
          {props.match_status}
        </span>
      </div>
      <div><strong>UTC Time:</strong> {props.acq_datetime}</div>
      <div><strong>FRP Energy:</strong> {Number(props.frp).toFixed(2)} MW</div>
      <div><strong>Confidence:</strong> {props.confidence_tier} ({props.raw_confidence})</div>
      <div><strong>H3 Cell (Res-5):</strong> <code>{props.h3_index}</code></div>
      {props.nearest_dist_km !== null && (
        <div style={{ marginTop: '5px', paddingTop: '5px', borderTop: '1px solid #cbd5e1' }}>
          <strong>Cross-Sensor Link:</strong> {props.nearest_dist_km.toFixed(2)} km • {Math.round(props.time_diff_min || 0)} min apart
        </div>
      )}
    </div>
  )
}