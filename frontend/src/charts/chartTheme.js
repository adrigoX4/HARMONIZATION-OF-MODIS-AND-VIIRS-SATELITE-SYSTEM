import { fmtCompact } from '../lib/format.js'

// Series colours come from the theme tokens in App.css, so charts follow
// the light/dark switch without re-rendering.
export const SERIES = {
  lead: 'var(--series-lead)',
  modis: 'var(--series-modis)',
  viirs: 'var(--series-viirs)',
  matched: 'var(--series-matched)',
}

const MONO = "'IBM Plex Mono', ui-monospace, Consolas, monospace"

export const gridProps = {
  stroke: 'var(--line)',
  vertical: false,
}

export const axisProps = {
  stroke: 'transparent',
  tickLine: false,
  axisLine: false,
  tick: { fill: 'var(--text-3)', fontSize: 11, fontFamily: MONO },
}

export const yAxisProps = {
  ...axisProps,
  width: 44,
  tickFormatter: fmtCompact,
}

export const tooltipProps = {
  cursor: { fill: 'var(--hover-wash)', stroke: 'var(--line-strong)' },
  contentStyle: {
    background: 'var(--bg-2)',
    border: '1px solid var(--line-strong)',
    borderRadius: 'var(--r-ctl)',
    boxShadow: 'var(--shadow-float)',
    fontFamily: MONO,
    fontSize: 12,
    padding: '8px 12px',
  },
  labelStyle: { color: 'var(--text-2)', marginBottom: 4 },
  itemStyle: { color: 'var(--text-1)', padding: 0 },
  formatter: (v) => Number(v).toLocaleString('en-US'),
}
