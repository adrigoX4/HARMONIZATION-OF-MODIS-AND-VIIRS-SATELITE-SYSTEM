import React from 'react'
import { Info } from 'lucide-react'

export default function ScientificDisclaimer() {
  return (
    <footer className="disclaimer-banner">
      <Info size={16} color="#06b6d4" style={{ flexShrink: 0 }} />
      <span>
        <strong>Scientific Methodological Note:</strong> Harmonized detections link 1 km MODIS and 375 m VIIRS thermal anomalies within ≤ 1.5 km and ≤ 4 hours to bridge orbital overpass gaps without double-counting. Anomaly indicators measure statistical departure from H3 Resolution-5 historical seasonal baselines and do not constitute real-time wildfire spread forecasts.
      </span>
    </footer>
  )
}