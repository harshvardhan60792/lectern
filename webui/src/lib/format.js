export const fmt = (n, digits = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? '—' : Number(n).toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })

export const plural = (n, word) => `${fmt(n)} ${word}${n === 1 ? '' : 's'}`

export const pct = (n, digits = 0) => (n === null || n === undefined ? '—' : `${fmt(n, digits)}%`)

export const initials = (name = '') =>
  name.split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('') || '·'

export const statusTone = { completed: 'good', active: 'brass', failed: 'warn', withdrawn: 'bad' }
export const statusText = { completed: 'Completed', active: 'Active', failed: 'Failed', withdrawn: 'Withdrawn' }

export const sourceText = { oulad: 'Open University', assistments: 'ASSISTments', local: 'Added here', openstax: 'OpenStax', sciq: 'SciQ' }

export const masteryTone = (v) => (v === null || v === undefined ? 'none' : v >= 75 ? 'good' : v >= 50 ? 'warn' : 'bad')

export const dateText = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso.length <= 10 ? `${iso}T12:00:00` : iso.replace(' ', 'T'))
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
