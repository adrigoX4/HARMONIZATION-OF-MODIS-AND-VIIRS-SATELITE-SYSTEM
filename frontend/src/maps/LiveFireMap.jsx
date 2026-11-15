import React, { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl, Pane, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import Skeleton from '../components/Skeleton.jsx';

// Dots are coloured ONLY by sensor category. Colours live in the theme tokens
// (--cat-*) in App.css; Leaflet draws on canvas, which can't read CSS
// variables, so they're resolved once from the document with these fallbacks.
// Listed bottom-to-top: each category gets its own pane, so the rare ones
// (Possible match, Matched) are always drawn above the common ones.
const CATEGORIES = [
  { status: 'MODIS-only', label: 'MODIS-only', token: '--cat-modis', fallback: '#3b82f6', z: 401 },
  { status: 'VIIRS-only', label: 'VIIRS-only', token: '--cat-viirs', fallback: '#ff6b3d', z: 402 },
  { status: 'Possible Match', label: 'Possible match', token: '--cat-possible', fallback: '#e11d74', z: 403 },
  { status: 'Matched', label: 'Matched MODIS+VIIRS', token: '--cat-matched', fallback: '#22c55e', z: 404 },
];
// Legend reads in the order the request listed them
const LEGEND_ORDER = ['MODIS-only', 'VIIRS-only', 'Matched', 'Possible Match'];

const categoryOf = (p) => (CATEGORIES.some((c) => c.status === p.match_status) ? p.match_status : 'VIIRS-only');

function useCategoryColors() {
  return useMemo(() => {
    const css = typeof window !== 'undefined' ? getComputedStyle(document.documentElement) : null;
    return Object.fromEntries(
      CATEGORIES.map((c) => [c.status, (css && css.getPropertyValue(c.token).trim()) || c.fallback])
    );
  }, []);
}

// One fixed dot size, a touch larger when zoomed in.
const radiusForZoom = (zoom) => 5 + Math.min(3, Math.max(0, zoom - 4)) * 0.75;

const GIBS = (layer, date, matrix, ext) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/${date}/${matrix}/{z}/{y}/{x}.${ext}`;

function ViewportController({ bbox }) {
  const map = useMap();
  useEffect(() => {
    if (!bbox) return;
    const parts = bbox.split(',').map(Number);
    if (parts.length !== 4 || parts.some(Number.isNaN)) return;
    const [w, s, e, n] = parts;
    if (w <= -175 && e >= 175) {
      map.setView([18, 12], 2, { animate: true });
    } else {
      map.fitBounds(
        [
          [Math.max(-85, s), Math.max(-180, w)],
          [Math.min(85, n), Math.min(180, e)],
        ],
        { padding: [28, 28], maxZoom: 8, animate: true }
      );
    }
  }, [bbox, map]);
  return null;
}

function ZoomWatcher({ onZoom }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => onZoom(map.getZoom()), [map, onZoom]);
  return null;
}

function Swatch({ color }) {
  return (
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: color,
        border: '1px solid #ffffff',
        boxShadow: '0 0 0 1px rgba(0, 0, 0, 0.25)',
        flexShrink: 0,
      }}
    />
  );
}

function MapLegend({ colors, counts, hidden, onToggle, shown, total }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: 12,
        bottom: 12,
        zIndex: 1000,
        padding: '10px 12px',
        borderRadius: 'var(--r-ctl)',
        background: 'var(--overlay)',
        border: '1px solid var(--line-strong)',
        boxShadow: 'var(--shadow-float)',
        color: 'var(--text-1)',
        fontFamily: 'var(--font-sans)',
        fontVariantNumeric: 'tabular-nums',
        fontSize: 11,
        lineHeight: '16px',
        display: 'grid',
        gap: 2,
        minWidth: 232,
      }}
    >
      <div style={{ color: 'var(--text-3)', fontWeight: 500, marginBottom: 2 }}>Detections</div>
      {LEGEND_ORDER.map((status) => {
        const cat = CATEGORIES.find((c) => c.status === status);
        const isHidden = hidden.has(status);
        return (
          <button
            key={status}
            type="button"
            onClick={() => onToggle(status)}
            aria-pressed={!isHidden}
            title={isHidden ? `Show ${cat.label}` : `Hide ${cat.label}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              width: '100%',
              padding: '2px 4px',
              margin: '0 -4px',
              border: 0,
              borderRadius: 4,
              background: 'transparent',
              color: 'inherit',
              font: 'inherit',
              textAlign: 'left',
              cursor: 'pointer',
              opacity: isHidden ? 0.4 : 1,
              transition: 'opacity 140ms var(--ease)',
            }}
          >
            <Swatch color={colors[status]} />
            <span style={{ flex: 1, whiteSpace: 'nowrap', textDecoration: isHidden ? 'line-through' : 'none' }}>
              {cat.label}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>
              {(counts[status] || 0).toLocaleString('en-US')}
            </span>
          </button>
        );
      })}
      {total > shown && (
        <div
          style={{
            marginTop: 6,
            paddingTop: 6,
            borderTop: '1px solid var(--line)',
            color: 'var(--text-2)',
          }}
        >
          Showing {shown.toLocaleString('en-US')} of {total.toLocaleString('en-US')} detections
        </div>
      )}
    </div>
  );
}

// Covers the map until the first base tiles have loaded and fire points are in,
// then fades out. A timeout keeps a slow or blocked tile server from pinning it.
function MapSkeleton({ ready }) {
  return (
    <div className="map-skeleton" style={{ opacity: ready ? 0 : 1, pointerEvents: ready ? 'none' : 'auto' }} aria-hidden={ready}>
      <Skeleton width="100%" height="100%" radius={0} />
      <Skeleton
        raised
        width={232}
        height={136}
        radius="var(--r-ctl)"
        style={{ position: 'absolute', left: 12, bottom: 12 }}
      />
    </div>
  );
}

function FirePopup({ p, lat, lon, color }) {
  return (
    <Popup>
      <div style={{ minWidth: 215, fontSize: 12, lineHeight: '18px', display: 'grid', gap: 2 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
            paddingBottom: 4,
            marginBottom: 2,
            borderBottom: '1px solid var(--line-strong)',
          }}
        >
          <strong>{p.instrument || p.sensor_family}</strong>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <Swatch color={color} />
            {p.match_status}
          </span>
        </div>
        <div><strong>Coords:</strong> {lat.toFixed(4)}°, {lon.toFixed(4)}°</div>
        <div><strong>UTC Time:</strong> {p.acq_datetime || p.utc_date}</div>
        <div>
          <strong>FRP:</strong>{' '}
          <span style={{ fontFamily: 'var(--font-mono, monospace)' }}>{Number(p.frp || 0).toFixed(2)} MW</span>
        </div>
        <div>
          <strong>Resolution:</strong> {p.spatial_res_m} m • <strong>H3:</strong>{' '}
          <span style={{ fontFamily: 'var(--font-mono, monospace)' }}>{p.h3_index || 'N/A'}</span>
        </div>
        {p.match_id && (
          <div
            style={{
              marginTop: 4,
              padding: '4px 6px',
              borderRadius: 4,
              background: 'var(--success-soft)',
              color: 'var(--success-ink)',
              fontSize: 11,
            }}
          >
            <strong>Pair:</strong> {p.match_id} ({p.nearest_dist_km} km, {p.time_diff_min} min)
          </div>
        )}
      </div>
    </Popup>
  );
}

// Accepts both prop shapes in use: { bbox, gibsDate } and { region, selectedDate }.
export default function LiveFireMap({ geojson, bbox, region, height = '520px', gibsDate, selectedDate, loading = false }) {
  const [tilesReady, setTilesReady] = useState(false);
  useEffect(() => {
    if (tilesReady) return undefined;
    const t = setTimeout(() => setTilesReady(true), 6000);
    return () => clearTimeout(t);
  }, [tilesReady]);
  const ready = tilesReady && !loading;

  const colors = useCategoryColors();
  const [hidden, setHidden] = useState(() => new Set());
  const [zoom, setZoom] = useState(2);
  const radius = radiusForZoom(zoom);

  const features = geojson?.features || [];
  const layerDate = gibsDate || selectedDate || '2026-10-31';
  const activeBbox = bbox || region?.bbox;
  const cssHeight = typeof height === 'number' ? `${height}px` : height;

  // Points grouped by category; one pass over the features.
  const byCategory = useMemo(() => {
    const groups = Object.fromEntries(CATEGORIES.map((c) => [c.status, []]));
    features.forEach((feat, idx) => groups[categoryOf(feat.properties || {})].push({ feat, idx }));
    return groups;
  }, [features]);

  // Counts cover every detection behind the map (backend `category_counts`),
  // falling back to the drawn points when the API doesn't send them.
  const counts = useMemo(() => {
    if (geojson?.category_counts) return geojson.category_counts;
    return Object.fromEntries(CATEGORIES.map((c) => [c.status, byCategory[c.status].length]));
  }, [geojson, byCategory]);

  const toggle = (status) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });

  return (
    <div
      className="map-frame"
      aria-busy={!ready}
      style={{
        height: cssHeight,
        width: '100%',
        overflow: 'hidden',
        borderRadius: 'var(--r-map)',
        border: '1px solid var(--line)',
        background: '#0b1a2a',
      }}
    >
      <MapContainer
        preferCanvas={true}
        center={[18, 12]}
        zoom={2}
        minZoom={2}
        maxBounds={[[-85, -180], [85, 180]]}
        maxBoundsViscosity={1.0}
        style={{ height: '100%', width: '100%', background: '#0b1a2a' }}
        scrollWheelZoom={true}
      >
        <ViewportController bbox={activeBbox} />
        <ZoomWatcher onZoom={setZoom} />
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Esri World Imagery (Satellite)">
            <TileLayer
              attribution="Tiles &copy; Esri, Maxar, Earthstar Geographics"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              noWrap={true}
              eventHandlers={{ load: () => setTilesReady(true) }}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="NASA GIBS Blue Marble">
            <TileLayer
              attribution="NASA EOSDIS GIBS · Blue Marble"
              url={GIBS('BlueMarble_ShadedRelief_Bathymetry', '2004-08-01', 'GoogleMapsCompatible_Level8', 'jpg')}
              maxNativeZoom={8}
              noWrap={true}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name={`NASA GIBS VIIRS True Color (${layerDate})`}>
            <TileLayer
              attribution="NASA EOSDIS GIBS · VIIRS SNPP Corrected Reflectance"
              url={GIBS('VIIRS_SNPP_CorrectedReflectance_TrueColor', layerDate, 'GoogleMapsCompatible_Level9', 'jpg')}
              maxNativeZoom={9}
              noWrap={true}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Esri Dark Gray Canvas">
            <TileLayer
              attribution="Tiles &copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
              noWrap={true}
            />
          </LayersControl.BaseLayer>
          <LayersControl.Overlay checked name="Country boundaries & places (Esri)">
            <TileLayer
              attribution="Boundaries &copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
              noWrap={true}
              zIndex={650}
            />
          </LayersControl.Overlay>
        </LayersControl>

        {CATEGORIES.map((cat) => (
          <Pane key={cat.status} name={`fire-${cat.z}`} style={{ zIndex: cat.z }}>
            {!hidden.has(cat.status) &&
              byCategory[cat.status].map(({ feat, idx }) => {
                const [lon, lat] = feat.geometry.coordinates;
                const p = feat.properties || {};
                return (
                  <CircleMarker
                    key={`${p.source_id || idx}-${idx}`}
                    center={[lat, lon]}
                    radius={radius}
                    pathOptions={{
                      fillColor: colors[cat.status],
                      color: '#ffffff',
                      weight: 1,
                      opacity: 0.85,
                      fillOpacity: 0.85,
                    }}
                  >
                    <FirePopup p={p} lat={lat} lon={lon} color={colors[cat.status]} />
                  </CircleMarker>
                );
              })}
          </Pane>
        ))}
      </MapContainer>
      <MapLegend
        colors={colors}
        counts={counts}
        hidden={hidden}
        onToggle={toggle}
        shown={features.length}
        total={geojson?.total_available ?? features.length}
      />
      <MapSkeleton ready={ready} />
    </div>
  );
}
