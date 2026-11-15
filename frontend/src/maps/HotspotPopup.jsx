import React from 'react'
import { fmtNum } from '../lib/format.js'

const STATUS_CLASS = {
  Matched: 'status-matched',
  'Possible Match': 'status-possible',
  'MODIS-only': 'status-modis',
  'VIIRS-only': 'status-viirs',
}

export default function HotspotPopup({ props }) {
  return (
    <div style={{ minWidth: 224 }}>
      <div className="popup-head">
        <span>
          {props.sensor_family} · {props.spatial_res_m} m
        </span>
        <span className={`status ${STATUS_CLASS[props.match_status] || ''}`} style={{ fontSize: 12, fontWeight: 400 }}>
          {props.match_status}
        </span>
      </div>
      <dl className="popup-grid">
        <dt>UTC</dt>
        <dd>{props.acq_datetime}</dd>
        <dt>FRP</dt>
        <dd>{fmtNum(props.frp, 1)} MW</dd>
        <dt>Conf</dt>
        <dd>
          {props.confidence_tier} ({props.raw_confidence})
        </dd>
        <dt>H3</dt>
        <dd>{props.h3_index}</dd>
      </dl>
      {props.nearest_dist_km !== null && props.nearest_dist_km !== undefined && (
        <dl className="popup-grid popup-link">
          <dt>Link</dt>
          <dd>
            {fmtNum(props.nearest_dist_km, 2)} km · {Math.round(props.time_diff_min || 0)} min apart
          </dd>
        </dl>
      )}
    </div>
  )
}
