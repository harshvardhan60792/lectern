import { RefreshCw } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { TiltCard } from '../components/depth'
import { Button, Empty, Loading, PageHead, Pill, Select, Stat, Table, Tabs } from '../components/ui'
import { api } from '../lib/api'
import { fmt } from '../lib/format'
import { useApi } from '../lib/useApi'

const LEVEL = { high: 'bad', medium: 'warn', low: 'good' }
const FEATURE = {
  days_since_active: 'Days since last activity', recent_clicks: 'Activity in the last two weeks', active_days: 'Number of active days',
  submission_rate: 'Share of work handed in', avg_score: 'Average score', late_registration: 'Late registration', prev_attempts: 'Earlier attempts',
}

/** A gauge needle that swings to the student's risk. */
function Gauge({ value }) {
  return (
    <svg width="190" height="110" viewBox="0 0 190 110" aria-label={`${Math.round(value * 100)}% risk`}>
      <path d="M15 100 A80 80 0 0 1 175 100" fill="none" stroke="var(--line)" strokeWidth="12" strokeLinecap="round" />
      <path d="M15 100 A80 80 0 0 1 175 100" fill="none" stroke="url(#riskgrad)" strokeWidth="12" strokeLinecap="round" opacity=".9" />
      <defs>
        <linearGradient id="riskgrad"><stop offset="0" stopColor="var(--green)" /><stop offset=".55" stopColor="var(--amber)" /><stop offset="1" stopColor="var(--red)" /></linearGradient>
      </defs>
      <motion.line x1="95" y1="100" stroke="var(--ink)" strokeWidth="3" strokeLinecap="round"
        initial={{ x2: 29, y2: 100 }} animate={{ x2: 95 + 66 * Math.cos(Math.PI * (1 - value)), y2: 100 - 66 * Math.sin(Math.PI * (1 - value)) }}
        transition={{ type: 'spring', stiffness: 90, damping: 14 }} />
      <circle cx="95" cy="100" r="7" fill="var(--ink)" />
    </svg>
  )
}

export default function Risk({ session }) {
  const courses = useApi('courses_search', {}, [])
  const [course, setCourse] = useState('')
  const [day, setDay] = useState('60')
  const [picked, setPicked] = useState(null)
  const model = useApi('model_run', {}, [])
  const { data, loading } = useApi(course ? 'risk_predict' : null, { course_id: Number(course), day: Number(day) }, [course, day])
  const options = (courses.data || []).filter((c) => c.source !== 'assistments' && c.enrolled)
  useEffect(() => {
    if (!course && options.length) setCourse(String(options.find((c) => c.code === 'DDD-2014J')?.id || options[0].id))
  }, [options.length]) // eslint-disable-line
  useEffect(() => setPicked(null), [course, day])
  const check = data?.check
  const flagged = data ? data.predictions.filter((p) => p.risk >= data.threshold).length : 0

  return (
    <>
      <PageHead title="At-risk students" sub="Who is unlikely to finish, judged on a chosen day of the course. For Open University courses each prediction sits next to what really happened."
        actions={session.role === 'admin' && <Button kind="secondary" icon={RefreshCw} onClick={async () => { const r = await api('model_retrain'); toast.success(`Retrained. ROC AUC ${fmt(r.roc_auc, 3)}`); model.reload() }}>Retrain model</Button>} />
      <div className="row wrap" style={{ marginBottom: 18 }}>
        <Select label="Course" value={course} onChange={setCourse} width={380} options={options.map((c) => ({ value: c.id, label: `${c.code}  ${c.title}` }))} />
        <span className="small muted">as of course day</span>
        <Tabs id="day" value={day} onChange={setDay} items={['30', '60', '90', '120']} />
      </div>

      {data && (
        <div className="stat-row" style={{ marginBottom: 20 }}>
          <Stat label="Still enrolled" value={fmt(data.total)} note={`on day ${day}`} />
          <Stat label="Flagged at risk" value={fmt(flagged)} note="risk 50% or more" tone={flagged ? 'red' : undefined} />
          {check?.flagged > 0 && <Stat label="Flagged who didn't finish" value={`${fmt(check.precision * 100)}%`} note={`${fmt(check.flagged_correct)} of ${fmt(check.flagged)} withdrew or failed`} />}
          {check?.did_not_finish > 0 && <Stat label="Non-finishers caught" value={`${fmt(check.recall * 100)}%`} note={`${fmt(check.flagged_correct)} of ${fmt(check.did_not_finish)} flagged by day ${day}`} />}
        </div>
      )}

      <div className="split-wide" style={{ alignItems: 'start' }}>
        {!data || loading ? <Loading height={480} /> : (
          <Table rowKey="student_id" rows={data.predictions} onRowClick={setPicked} selectedKey={picked?.student_id} maxHeight="calc(100vh - 360px)"
            empty={<Empty title="Nobody was still enrolled that day">Try an earlier day.</Empty>}
            columns={[
              { key: 'name', label: 'Student' },
              { key: 'risk', label: 'Risk', align: 'r', render: (r) => `${fmt(r.risk * 100)}%` },
              { key: 'level', label: 'Level', render: (r) => <Pill tone={LEVEL[r.level]} dot>{r.level}</Pill> },
              { key: 'reason', label: 'Main reason', wrap: true, render: (r) => r.reasons[0] || '—' },
              { key: 'outcome', label: 'What happened', render: (r) => r.outcome || 'Still active' },
            ]} />
        )}
        <div className="stack" style={{ position: 'sticky', top: 0, gap: 16 }}>
          {picked ? (
            <motion.div key={picked.student_id} initial={{ opacity: 0, x: 20, rotateY: -10 }} animate={{ opacity: 1, x: 0, rotateY: 0 }} transition={{ type: 'spring', stiffness: 260, damping: 24 }} style={{ transformPerspective: 1000 }}>
              <div className="card card-pad stack">
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <h2 className="card-title">{picked.name}</h2>
                  <Pill tone={LEVEL[picked.level]} dot>{picked.level} risk</Pill>
                </div>
                <div className="row" style={{ gap: 18 }}>
                  <Gauge value={picked.risk} />
                  <div className="read num" style={{ fontSize: 48 }}>{fmt(picked.risk * 100)}%</div>
                </div>
                <ul className="small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
                  {(picked.reasons.length ? picked.reasons : ['No single strong reason; several small ones add up.']).map((r) => <li key={r}>{r}</li>)}
                </ul>
                <p className="small muted">What happened: <b>{picked.outcome || 'Still active'}</b></p>
                {picked.nudge && (
                  <div className="card" style={{ background: 'var(--card-2)', boxShadow: 'none', padding: '12px 14px' }}>
                    <p className="xsmall faint" style={{ marginBottom: 4 }}>Suggested message</p>
                    <p className="small">{picked.nudge}</p>
                  </div>
                )}
              </div>
            </motion.div>
          ) : (
            <TiltCard className="card-pad" max={4}>
              <h2 className="card-title">The model</h2>
              {model.data ? (
                <div className="stack" style={{ marginTop: 8 }}>
                  <p className="small muted">Logistic regression on 7 behaviour measures, trained on {fmt(model.data.n_train)} snapshots of 2013 students and tested on {fmt(model.data.n_test)} from 2014.</p>
                  <div className="row" style={{ gap: 26 }}>
                    {[['ROC AUC', model.data.roc_auc], ['Precision', model.data.precision], ['Recall', model.data.recall]].map(([k, v]) => (
                      <div key={k}><div className="stat-label">{k}</div><div className="stat-value" style={{ fontSize: 28 }}>{fmt(v, 2)}</div></div>
                    ))}
                  </div>
                  <p className="small faint" style={{ marginTop: 6 }}>What moves the risk, and which way:</p>
                  {Object.entries(model.data.details.weights || {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).map(([k, v]) => (
                    <div key={k} className="row small" style={{ justifyContent: 'space-between' }}>
                      <span>{FEATURE[k] || k}</span>
                      <span style={{ color: v > 0 ? 'var(--red)' : 'var(--green)', fontWeight: 700 }}>{v > 0 ? 'raises risk' : 'lowers risk'} ({v > 0 ? '+' : ''}{fmt(v, 2)})</span>
                    </div>
                  ))}
                  <p className="xsmall faint" style={{ marginTop: 8 }}>Pick a student to see their reasons and a suggested message.</p>
                </div>
              ) : <Loading height={200} />}
            </TiltCard>
          )}
        </div>
      </div>
    </>
  )
}
