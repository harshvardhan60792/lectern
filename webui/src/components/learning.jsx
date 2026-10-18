// Pieces about a learner: mastery skyline, study calendar, coach notes, course map.
import { motion, useReducedMotion } from 'motion/react'
import { masteryTone } from '../lib/format'

const BLOCK = { good: ['#3F8058', '#2F6646', '#5C9A73'], warn: ['#B07A1C', '#8E6214', '#C9963E'], bad: ['#B64A39', '#933A2C', '#CB6A59'], none: ['#C9D0C2', '#AFB8A8', '#DCE1D5'] }

/**
 * Mastery as a small isometric skyline: one block per module, height = mastery.
 * Each block carries its number and module name in text, so colour is only a second cue.
 */
export function MasterySkyline({ tiles, limit = 40 }) {
  const reduce = useReducedMotion()
  const shown = tiles.length > limit ? tiles.filter((t) => t.mastery !== null).slice(0, limit) : tiles
  if (!shown.length) return <p className="muted small">No results to show yet.</p>
  const W = 40, DX = 16, DY = 9, GAP = 36, MAXH = 130, BASE = 175
  const width = shown.length * (W + GAP) + DX + 30
  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={width} height={BASE + 46} role="list" aria-label="Mastery by module" style={{ display: 'block' }}>
        <line x1="0" x2={width} y1={BASE + 0.5} y2={BASE + 0.5} stroke="var(--line)" />
        {shown.map((t, i) => {
          const tone = masteryTone(t.mastery)
          const [front, side, top] = BLOCK[tone]
          const h = t.mastery === null ? 6 : 10 + (t.mastery / 100) * MAXH
          const x = 24 + i * (W + GAP)
          const y = BASE - h
          const label = `${t.title}: ${t.mastery === null ? 'not started' : `${t.mastery}% mastery`}`
          const name = t.title.replace(/^\d+\.\s*/, '')
          return (
            <g key={t.module_id} role="listitem" aria-label={label}>
              <title>{`${label} (${t.basis})`}</title>
              <motion.g initial={reduce ? false : { scaleY: 0.04 }} animate={{ scaleY: 1 }} style={{ originY: 1, transformBox: 'fill-box' }}
                transition={{ type: 'spring', stiffness: 150, damping: 17, delay: i * 0.04 }}>
                {/* side, top, front: a box seen from the front-right */}
                <polygon points={`${x + W},${y} ${x + W + DX},${y - DY} ${x + W + DX},${BASE - DY} ${x + W},${BASE}`} fill={side} />
                <polygon points={`${x},${y} ${x + DX},${y - DY} ${x + W + DX},${y - DY} ${x + W},${y}`} fill={top} />
                <rect x={x} y={y} width={W} height={h} fill={front} />
              </motion.g>
              <text x={x + W / 2 + DX / 2} y={y - DY - 8} textAnchor="middle" fontFamily="var(--font-read)" fontSize="15"
                fill={tone === 'none' ? 'var(--ink-3)' : 'var(--ink)'}>{t.mastery === null ? '—' : t.mastery}</text>
              <text x={x + W / 2} y={BASE + 18} textAnchor="middle" fontSize="11" fill="var(--ink-2)">{name.length > 13 ? `${name.slice(0, 12)}…` : name}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/** A year of study days, darker = more activity. */
export function StudyCalendar({ year, days }) {
  const start = new Date(`${year}-01-01T12:00:00`)
  const offset = (start.getDay() + 6) % 7 // Monday first
  const values = Object.values(days).filter((v) => v > 0).sort((a, b) => a - b)
  const top = values[Math.floor(values.length * 0.95)] || 1
  const cells = []
  for (let i = 0; i < offset; i++) cells.push(<span key={`p${i}`} style={{ width: 12, height: 12 }} />)
  const d = new Date(start)
  const months = []
  let index = offset
  while (d.getFullYear() === year) {
    const iso = d.toISOString().slice(0, 10)
    const v = days[iso] || 0
    const level = v <= 0 ? 0 : Math.min(4, Math.ceil((v / top) * 4))
    if (d.getDate() === 1) months.push({ col: Math.floor(index / 7), name: d.toLocaleDateString('en-GB', { month: 'short' }) })
    cells.push(<span key={iso} className="cal-cell" data-l={level} title={`${iso}: ${v ? `${v} activity` : 'no study'}`} />)
    d.setDate(d.getDate() + 1)
    index++
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <div className="cal-months" style={{ position: 'relative', height: 14 }}>
        {months.map((m) => <span key={m.name} style={{ position: 'absolute', left: m.col * 15 }}>{m.name}</span>)}
      </div>
      <div className="cal" role="img" aria-label={`Study days in ${year}: ${Object.keys(days).length} active days`}>{cells}</div>
      <div className="row xsmall faint" style={{ gap: 6, marginTop: 8 }}>
        Less {[0, 1, 2, 3, 4].map((l) => <span key={l} className="cal-cell" data-l={l} />)} More
      </div>
    </div>
  )
}

/** Coach notes: the most urgent have a brass rule beside them. */
export function CoachNotes({ notes }) {
  if (!notes.length) return <p className="muted small">Nothing to flag. Keep going.</p>
  return (
    <div className="stack" style={{ gap: 14 }}>
      {notes.map((n, i) => (
        <motion.div key={n.rule + i} className="row" style={{ alignItems: 'stretch', gap: 12 }}
          initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.08 * i, duration: 0.25 }}>
          <span style={{ width: 3, borderRadius: 2, flex: 'none', background: n.priority === 1 ? 'var(--brass)' : 'var(--line)' }} />
          <p style={{ fontSize: 'var(--fs-sm)', lineHeight: 1.5 }}>{n.text}</p>
        </motion.div>
      ))}
    </div>
  )
}

/** Prerequisite graph laid out in columns by depth, with drawn arrows. */
export function CourseMap({ nodes, edges, completed = [] }) {
  if (!nodes.length) return <p className="muted small">No course requires another yet.</p>
  const depth = Object.fromEntries(nodes.map((n) => [n.id, 0]))
  for (let k = 0; k < nodes.length; k++) edges.forEach(([a, b]) => { depth[b] = Math.max(depth[b], depth[a] + 1) })
  const cols = {}
  nodes.forEach((n) => { (cols[depth[n.id]] ||= []).push(n) })
  const W = 240, H = 64, XG = 90, YG = 22
  const pos = {}
  Object.entries(cols).forEach(([c, items]) => items.forEach((n, i) => { pos[n.id] = { x: c * (W + XG), y: i * (H + YG) } }))
  const width = (Object.keys(cols).length) * (W + XG)
  const height = Math.max(...Object.values(cols).map((v) => v.length)) * (H + YG)
  return (
    <div style={{ position: 'relative', width, height, maxWidth: '100%' }}>
      <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }} aria-hidden>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)" />
          </marker>
        </defs>
        {edges.map(([a, b]) => {
          const p = pos[a], q = pos[b]
          const x1 = p.x + W, y1 = p.y + H / 2, x2 = q.x, y2 = q.y + H / 2
          return <motion.path key={`${a}-${b}`} d={`M${x1},${y1} C${x1 + 45},${y1} ${x2 - 45},${y2} ${x2 - 2},${y2}`}
            fill="none" stroke="var(--ink-3)" strokeWidth="1.6" markerEnd="url(#arrow)"
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.8 }} />
        })}
      </svg>
      {nodes.map((n) => (
        <div key={n.id} className={`map-node ${completed.includes(n.id) ? 'done' : ''}`}
          style={{ position: 'absolute', left: pos[n.id].x, top: pos[n.id].y, width: W, height: H }}>
          <div className="xsmall" style={{ color: 'var(--brass-ink)', fontWeight: 700 }}>{n.code}</div>
          <div className="small" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{n.title}</div>
        </div>
      ))}
    </div>
  )
}
