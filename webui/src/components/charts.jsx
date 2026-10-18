// Small SVG charts drawn to the Lectern palette. Each one labels values in text,
// so nothing depends on colour alone.
import { motion, useReducedMotion } from 'motion/react'
import { useMemo } from 'react'
import { fmt } from '../lib/format'

export const RESULT_COLOR = {
  Distinction: 'var(--ink)', Pass: 'var(--green)', completed: 'var(--green)',
  Fail: 'var(--amber)', failed: 'var(--amber)', Withdrawn: 'var(--red)', withdrawn: 'var(--red)',
  active: 'var(--brass)',
}

function Legend({ items }) {
  return (
    <div className="row wrap" style={{ gap: 16, marginTop: 10 }}>
      {items.map((it) => (
        <span key={it} className="row xsmall muted" style={{ gap: 6 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: RESULT_COLOR[it] || 'var(--brass)' }} />{it}
        </span>
      ))}
    </div>
  )
}

/** 100% stacked horizontal bars: e.g. passed / failed / withdrew per group. */
export function StackedBars({ rows, keys = ['Pass', 'Fail', 'Withdrawn'], labelWidth = 170, rowHeight = 26 }) {
  const reduce = useReducedMotion()
  const W = 900
  const H = rows.length * (rowHeight + 10)
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Share of results per group">
        {rows.map((r, i) => {
          const y = i * (rowHeight + 10)
          let x = labelWidth
          const total = keys.reduce((s, k) => s + (r.parts[k] || 0), 0) || 1
          return (
            <g key={r.label}>
              <text x={labelWidth - 12} y={y + rowHeight / 2 + 5} textAnchor="end" fontSize="14" fill="var(--ink-2)">{r.label}</text>
              {keys.map((k, j) => {
                const w = ((r.parts[k] || 0) / total) * (W - labelWidth - 4)
                const x0 = x
                x += w
                return (
                  <g key={k}>
                    <motion.rect x={x0} y={y} height={rowHeight} width={w} rx={j === 0 ? 3 : 0} fill={RESULT_COLOR[k]}
                      initial={reduce ? false : { scaleX: 0 }} animate={{ scaleX: 1 }} style={{ originX: 0, transformBox: 'fill-box' }}
                      transition={{ duration: 0.6, delay: i * 0.025 + j * 0.08, ease: [0.2, 0.8, 0.2, 1] }} />
                    {w > 46 && (
                      <text x={x0 + w / 2} y={y + rowHeight / 2 + 5} textAnchor="middle" fontSize="13" fontWeight="700" fill="#F6F7F2">
                        {Math.round(((r.parts[k] || 0) / total) * 100)}%
                      </text>
                    )}
                  </g>
                )
              })}
            </g>
          )
        })}
      </svg>
      <Legend items={keys} />
    </div>
  )
}

/** Horizontal bars with values written at the end. */
export function Bars({ data, unit = '', labelWidth = 130, color, max }) {
  const reduce = useReducedMotion()
  const W = 640
  const top = max ?? Math.max(...data.map((d) => d.value || 0), 1)
  return (
    <svg viewBox={`0 0 ${W} ${data.length * 36}`} width="100%" role="img" aria-label="Bar chart">
      {data.map((d, i) => {
        const w = ((d.value || 0) / top) * (W - labelWidth - 90)
        return (
          <g key={d.label} transform={`translate(0 ${i * 36})`}>
            <text x={labelWidth - 12} y={20} textAnchor="end" fontSize="14" fill="var(--ink-2)">{d.label}</text>
            <motion.rect x={labelWidth} y={5} height={22} rx={3} width={w} fill={d.color || color || RESULT_COLOR[d.label] || 'var(--brass)'}
              initial={reduce ? false : { scaleX: 0 }} animate={{ scaleX: 1 }} style={{ originX: 0, transformBox: 'fill-box' }}
              transition={{ duration: 0.55, delay: i * 0.05, ease: [0.2, 0.8, 0.2, 1] }} />
            <text x={labelWidth + w + 8} y={20} fontSize="14" fill="var(--ink)" fontWeight="700">{fmt(d.value, d.digits ?? 0)}{unit}</text>
          </g>
        )
      })}
    </svg>
  )
}

/** Line chart; lines draw themselves in once. */
export function Lines({ x, series, xLabel, yLabel, height = 260 }) {
  const reduce = useReducedMotion()
  const W = 900, H = height, L = 54, R = 16, T = 16, B = 40
  const all = Object.values(series).flat()
  const yMax = Math.max(...all, 1) * 1.08
  const sx = (i) => L + (i / Math.max(1, x.length - 1)) * (W - L - R)
  const sy = (v) => T + (1 - v / yMax) * (H - T - B)
  const ticks = 4
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${yLabel} by ${xLabel}`}>
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const v = (yMax / ticks) * i
          return (
            <g key={i}>
              <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke="var(--line-soft)" />
              <text x={L - 8} y={sy(v) + 4} textAnchor="end" fontSize="12" fill="var(--ink-3)">{fmt(v)}</text>
            </g>
          )
        })}
        {x.map((v, i) => (i % Math.ceil(x.length / 10) === 0) && (
          <text key={i} x={sx(i)} y={H - B + 18} textAnchor="middle" fontSize="12" fill="var(--ink-3)">{v}</text>
        ))}
        <text x={(W + L) / 2} y={H - 4} textAnchor="middle" fontSize="12" fill="var(--ink-2)">{xLabel}</text>
        {Object.entries(series).map(([name, values], k) => {
          const d = values.map((v, i) => `${i ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join(' ')
          return (
            <motion.path key={name} d={d} fill="none" stroke={RESULT_COLOR[name] || 'var(--brass)'} strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round"
              initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1, delay: k * 0.12, ease: [0.2, 0.8, 0.2, 1] }} />
          )
        })}
      </svg>
      <Legend items={Object.keys(series)} />
    </div>
  )
}

/** Histogram with an optional marker line (e.g. the pass mark). */
export function Histogram({ values, bins = 25, min = 0, max = 100, mark, markLabel, height = 230, xLabel }) {
  const reduce = useReducedMotion()
  const counts = useMemo(() => {
    const c = new Array(bins).fill(0)
    values.forEach((v) => { c[Math.min(bins - 1, Math.max(0, Math.floor(((v - min) / (max - min)) * bins)))]++ })
    return c
  }, [values, bins, min, max])
  const W = 900, H = height, L = 48, B = 34, T = 22
  const top = Math.max(...counts, 1)
  const bw = (W - L - 10) / bins
  const sx = (v) => L + ((v - min) / (max - min)) * (W - L - 10)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Distribution">
      <line x1={L} x2={W - 10} y1={H - B} y2={H - B} stroke="var(--line)" />
      {counts.map((c, i) => {
        const h = (c / top) * (H - B - T)
        const lo = min + (i / bins) * (max - min)
        return (
          <motion.rect key={i} x={L + i * bw + 1.5} width={bw - 3} y={H - B - h} height={h} rx={2}
            fill={mark !== undefined && lo < mark ? 'var(--amber)' : 'var(--green)'}
            initial={reduce ? false : { scaleY: 0 }} animate={{ scaleY: 1 }} style={{ originY: 1, transformBox: 'fill-box' }}
            transition={{ duration: 0.5, delay: i * 0.015, ease: [0.2, 0.8, 0.2, 1] }}>
            <title>{`${Math.round(lo)}–${Math.round(lo + (max - min) / bins)}: ${c}`}</title>
          </motion.rect>
        )
      })}
      {[0, 25, 50, 75, 100].map((v) => <text key={v} x={sx(v)} y={H - B + 18} textAnchor="middle" fontSize="12" fill="var(--ink-3)">{v}</text>)}
      {mark !== undefined && (
        <g>
          <line x1={sx(mark)} x2={sx(mark)} y1={T - 8} y2={H - B} stroke="var(--ink)" strokeDasharray="4 4" />
          <text x={sx(mark) + 6} y={T} fontSize="13" fill="var(--ink)" fontWeight="700">{markLabel}</text>
        </g>
      )}
      {xLabel && <text x={(W + L) / 2} y={H - 2} textAnchor="middle" fontSize="12" fill="var(--ink-2)">{xLabel}</text>}
    </svg>
  )
}

/** Vertical columns for a time series. */
export function Columns({ data, height = 240 }) {
  const reduce = useReducedMotion()
  const W = 900, H = height, L = 46, B = 46, T = 14
  const top = Math.max(...data.map((d) => d.value), 1)
  const bw = (W - L - 8) / Math.max(1, data.length)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Columns">
      <line x1={L} x2={W - 8} y1={H - B} y2={H - B} stroke="var(--line)" />
      {data.map((d, i) => {
        const h = (d.value / top) * (H - B - T)
        return (
          <g key={d.label}>
            <motion.rect x={L + i * bw + 2} width={Math.max(2, bw - 4)} y={H - B - h} height={h} rx={2} fill="var(--brass)"
              initial={reduce ? false : { scaleY: 0 }} animate={{ scaleY: 1 }} style={{ originY: 1, transformBox: 'fill-box' }}
              transition={{ duration: 0.5, delay: i * 0.012 }}>
              <title>{`${d.label}: ${d.value.toLocaleString()}`}</title>
            </motion.rect>
            {i % Math.ceil(data.length / 12) === 0 && (
              <text x={L + i * bw + bw / 2} y={H - B + 16} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{d.label}</text>
            )}
          </g>
        )
      })}
      <text x={L - 8} y={T + 10} textAnchor="end" fontSize="12" fill="var(--ink-3)">{fmt(top)}</text>
    </svg>
  )
}
