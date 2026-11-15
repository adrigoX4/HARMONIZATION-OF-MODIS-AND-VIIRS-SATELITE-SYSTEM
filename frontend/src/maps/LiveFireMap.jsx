import React from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl } from 'react-leaflet'
import HotspotPopup from './HotspotPopup.jsx'

const STATUS_COLORS = {
  Matched: '#10b981',
  'Possible Match': '#f59e0b',
  'MODIS-only': '#3b82f6',
  'VIIRS-only': '#ff5e3a',
}

const GIBS_TRUE_COLOR = (date) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`

// GIBS reference labels are served on the GoogleMapsCompatible_Level13 matrix set
const GIBS_REFERENCE_LABELS =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Reference_Labels_15m/default/GoogleMapsCompatible_Level13/{z}/{y}/{x}.png'

export default function LiveFireMap({ geojson, selectedDate }) {
  const gibsDate = selectedDate || '2026-11-02'
  const features = geojson?.features || []

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.9rem', flexWrap: 'wrap', marginBottom: '0.75rem', fontSize: '0.78rem' }}>
        {Object.entries(STATUS_COLORS).map(([label, color]) => (
          <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
            {label}
          </span>
        ))}
        <span style={{ color: '#94a3b8', marginLeft: 'auto' }}>
          {features.length} global thermal hotspots • Satellite basemap with NASA GIBS place labels
        </span>
      </div>

      <div className="map-container">
        <MapContainer center={[15, 12]} zoom={2} minZoom={2} worldCopyJump={true} style={{ height: '100%', width: '100%' }}>
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="Satellite (Esri World Imagery)">
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer name={`NASA GIBS VIIRS True Color (${gibsDate})`}>
              <TileLayer
                url={GIBS_TRUE_COLOR(gibsDate)}
                attribution="Imagery: NASA EOSDIS GIBS (VIIRS SNPP Corrected Reflectance)"
                maxZoom={9}
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer name="Dark Orbital Basemap (Esri)">
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri"
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer name="OpenStreetMap Terrain">
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution="&copy; OpenStreetMap contributors"
              />
            </LayersControl.BaseLayer>

            <LayersControl.Overlay checked name="Place Labels & Borders (NASA GIBS)">
              <TileLayer
                url={GIBS_REFERENCE_LABELS}
                attribution="Labels: NASA EOSDIS GIBS"
                opacity={0.7}
                zIndex={650}
              />
            </LayersControl.Overlay>
          </LayersControl>

          {features.map((feat, idx) => {
            const [lon, lat] = feat.geometry.coordinates
            const p = feat.properties
            const color = STATUS_COLORS[p.match_status] || '#ff5e3a'
            const radius =
              p.sensor_family === 'MODIS'
                ? Math.min(14, 7 + Math.sqrt(p.frp || 1) * 0.5)
                : Math.min(10, 4.5 + Math.sqrt(p.frp || 1) * 0.4)

            return (
              <CircleMarker
                key={`${p.source_id}-${idx}`}
                center={[lat, lon]}
                radius={radius}
                pathOptions={{
                  color: '#ffffff',
                  fillColor: color,
                  fillOpacity: 0.92,
                  weight: 1.4,
                  opacity: 0.9,
                }}
              >
                <Popup>
                  <HotspotPopup props={p} />
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}
