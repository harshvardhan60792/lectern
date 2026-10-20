// How values look on screen (numbers, dates, labels) and how things move.

export const fmt = (n, digits = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? '—' : Number(n).toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })

export const plural = (n, word) => `${fmt(n)} ${word}${n === 1 ? '' : 's'}`

export const pct = (n, digits = 0) => (n === null || n === undefined ? '—' : `${fmt(n, digits)}%`)

export const initials = (name = '') =>
  name.split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('') || '·'

export const statusTone = { completed: 'good', active: 'brass', failed: 'warn', withdrawn: 'bad' }
export const statusText = { completed: 'Completed', active: 'Active', failed: 'Failed', withdrawn: 'Withdrawn' }

export const sourceText = { oulad: 'Past course', assistments: 'Maths practice', local: 'Added here', openstax: 'Programming', sciq: 'Science' }

export const masteryTone = (v) => (v === null || v === undefined ? 'none' : v >= 75 ? 'good' : v >= 50 ? 'warn' : 'bad')

export const dateText = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso.length <= 10 ? `${iso}T12:00:00` : iso.replace(' ', 'T'))
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

// Shared motion language (see DESIGN.md › Motion).
export const spring = { type: 'spring', stiffness: 380, damping: 32, mass: 0.9 }
export const springSoft = { type: 'spring', stiffness: 220, damping: 26 }
export const ease = [0.2, 0.8, 0.2, 1]

// Screens slide in from the side they were picked from; never fade-up on load.
export const pageVariants = {
  initial: (dir) => ({ opacity: 0, x: dir * 28 }),
  enter: { opacity: 1, x: 0, transition: { ...springSoft, opacity: { duration: 0.2 } } },
  exit: (dir) => ({ opacity: 0, x: dir * -18, transition: { duration: 0.14, ease } }),
}
