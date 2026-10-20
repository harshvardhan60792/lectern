import { CornerDownLeft, Download } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button, PageHead, Table } from '../components/ui'
import { api, useApi } from '../lib/api'
import { fmt } from '../lib/format'

export default function Ask() {
  const examples = useApi('ask_examples', {}, [])
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const ask = async (q = question) => {
    setQuestion(q)
    if (!q.trim()) return
    setBusy(true)
    setError('')
    try { setAnswer(await api('ask', { question: q })) } catch (e) { setError(e.message); setAnswer(null) } finally { setBusy(false) }
  }

  const rows = answer ? answer.rows.map((r, i) => Object.fromEntries([['_i', i], ...answer.columns.map((c, k) => [c, r[k]])])) : []
  const single = answer && rows.length === 1 && answer.columns.length <= 3

  return (
    <>
      <PageHead title="Ask the data" sub="Type a question in plain English. Lectern turns it into SQL with fixed rules, shows you the SQL, and runs it read-only. Nothing you type can change the data." />
      <form className="card" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 10, marginBottom: 14 }} onSubmit={(e) => { e.preventDefault(); ask() }}>
        <input className="input" style={{ border: 0, boxShadow: 'none', fontSize: 'var(--fs-lg)', height: 48, background: 'transparent' }}
          placeholder="e.g. Withdrawal rate by region" value={question} onChange={(e) => setQuestion(e.target.value)} aria-label="Your question" autoFocus />
        <Button type="submit" icon={CornerDownLeft} disabled={busy}>{busy ? 'Working…' : 'Ask'}</Button>
      </form>
      <div className="row wrap" style={{ gap: 8, marginBottom: 24 }}>
        {(examples.data || []).slice(0, 8).map((e) => (
          <button key={e} className="pill" style={{ cursor: 'pointer', border: '1px solid var(--line)', height: 30, fontSize: 'var(--fs-sm)', fontWeight: 600 }} onClick={() => ask(e)}>{e}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div key="err" className="card card-pad" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.1 } }}>
            <p className="error-text" style={{ fontSize: 'var(--fs-md)' }}>{error}</p>
            <p className="small muted" style={{ margin: '10px 0 6px' }}>Questions that work:</p>
            <div className="stack" style={{ gap: 2 }}>
              {(examples.data || []).map((e) => <button key={e} className="btn btn-quiet btn-sm" style={{ justifyContent: 'flex-start' }} onClick={() => ask(e)}>{e}</button>)}
            </div>
          </motion.div>
        )}
        {answer && (
          <motion.div key={answer.question} className="stack" style={{ gap: 16 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }} transition={{ duration: 0.25 }}>
            <div className="split" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.1fr)', alignItems: 'start' }}>
              <div className="card card-pad">
                <p className="small faint">Understood as</p>
                <p className="read" style={{ fontSize: 22, lineHeight: 1.35, marginTop: 4 }}>{answer.understood}</p>
                {single && (
                  <div className="row wrap" style={{ gap: 34, marginTop: 18 }}>
                    {answer.columns.map((c) => (
                      <div key={c}>
                        <div className="stat-label">{c.replace(/_/g, ' ')}</div>
                        <div className="stat-value" style={{ fontSize: 46 }}>{typeof rows[0][c] === 'number' ? fmt(rows[0][c], Number.isInteger(rows[0][c]) ? 0 : 1) : (rows[0][c] ?? '—')}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="card" style={{ background: 'var(--slate)', color: 'var(--on-slate)', padding: '18px 20px' }}>
                <p className="small" style={{ color: 'var(--on-slate-2)', marginBottom: 8 }}>The SQL it ran (read-only)</p>
                <pre className="code" style={{ background: 'transparent', border: 0, color: 'var(--on-slate)', padding: 0, whiteSpace: 'pre-wrap' }}>{answer.shown_sql}</pre>
              </div>
            </div>
            <div className="row">
              <span className="small muted">{rows.length} row{rows.length === 1 ? '' : 's'}</span>
              <span className="spacer" />
              <Button kind="secondary" size="sm" icon={Download} disabled={!rows.length}
                onClick={async () => { const p = await api('export_csv', { name: 'ask_the_data', rows: rows.map(({ _i, ...r }) => r) }); toast.success(`Saved ${p.split(/[\\/]/).pop()}`) }}>Save as CSV</Button>
            </div>
            <Table rowKey="_i" rows={rows} maxHeight={440}
              columns={answer.columns.map((c) => ({ key: c, label: c.replace(/_/g, ' '), align: typeof rows[0]?.[c] === 'number' ? 'r' : undefined,
                render: (r) => (typeof r[c] === 'number' ? fmt(r[c], Number.isInteger(r[c]) ? 0 : 1) : (r[c] ?? '—')) }))} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
