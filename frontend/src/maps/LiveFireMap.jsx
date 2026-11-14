import React from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl } from 'react-leaflet'
import HotspotPopup from './HotspotPopup.jsx'

const STATUS_COLORS = {
  Matched: '#10b981',
  'Possible Match': '#f59e0b',
  'MODIS-only': '#3b82f6',
  'VIIRS-only': '#ff5e3a',
}

export default function LiveFireMap({ geojson, selectedDate }) {
  const gibsDate = selectedDate || '2026-11-10'
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
          {features.length} thermal hotspots • Switch NASA GIBS True-Color imagery in top-right layer menu
        </span>
      </div>

      <div className="map-container">
        <MapContainer center={[29.2, 77.8]} zoom={6} style={{ height: '100%', width: '100%' }}>
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="Dark Orbital Basemap (Esri)">
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
            <LayersControl.BaseLayer name="NASA GIBS VIIRS True Color">
              <TileLayer
                url={`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/${gibsDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`}
                attribution="NASA EOSDIS GIBS"
                maxZoom={9}
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {features.map((feat, idx) => {
            const [lon, lat] = feat.geometry.coordinates
            const p = feat.properties
            const color = STATUS_COLORS[p.match_status] || '#ff5e3a'
            const radius =
              p.sensor_family === 'MODIS'
                ? Math.min(13, 6 + Math.sqrt(p.frp || 1) * 0.45)
                : Math.min(9, 4 + Math.sqrt(p.frp || 1) * 0.35)

            return (
              <CircleMarker
                key={`${p.source_id}-${idx}`}
                center={[lat, lon]}
                radius={radius}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.78,
                  weight: p.sensor_family === 'MODIS' ? 2 : 1,
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