import React from 'react'
import { Info } from 'lucide-react'

export default function ScientificDisclaimer() {
  return (
    <footer className="disclaimer-banner">
      <Info size={16} strokeWidth={1.5} absoluteStrokeWidth />
      <p>
        <span className="disclaimer-label">Method</span>
        Harmonized detections link 1 km MODIS and 375 m VIIRS thermal anomalies within 1.5 km and 4 hours to bridge
        orbital overpass gaps without double-counting. Anomaly indicators measure statistical departure from H3
        resolution 5 seasonal baselines. They do not forecast wildfire spread.
      </p>
    </footer>
  )
}
