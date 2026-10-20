import { motion } from 'motion/react'
import { Bars, StackedBars } from '../components/charts'
import { Float, TiltCard } from '../components/depth'
import { Button, Loading, PageHead, Stat } from '../components/ui'
import { useApi } from '../lib/api'
import { fmt, pct } from '../lib/format'

/** Index cards drifting on the slate: real numbers from the database, not decoration copy. */
function HeroCards({ totals }) {
  const cards = [
    { title: 'Answers logged', lines: [`${fmt(totals.answers)} answers`, `${fmt(totals.questions)} live questions`], x: '6%', y: 40, r: -7, d: 0 },
    { title: 'Certificates', lines: [`${fmt(totals.certificates)} issued`, 'each with a SHA-256 fingerprint'], x: '38%', y: 18, r: 4, d: 1.1 },
    { title: 'Completion', lines: [`${pct(totals.completion_rate, 1)} of ended enrollments`, `${fmt(totals.active)} still active`], x: '24%', y: 150, r: -2, d: 2.2 },
  ]
  return (
    <div className="hero-cards" aria-hidden>
      {cards.map((c) => (
        <Float key={c.title} delay={c.d} distance={9} rotate={1.4} style={{ position: 'absolute', left: c.x, top: c.y }}>
          <motion.div className="hero-card" style={{ rotate: c.r }}
            initial={{ opacity: 0, y: 40, rotateX: 30 }} animate={{ opacity: 1, y: 0, rotateX: 0 }}
            transition={{ type: 'spring', stiffness: 120, damping: 16, delay: 0.15 + c.d * 0.12 }}>
            <b>{c.title}</b>
            {c.lines.map((l) => <div key={l}>{l}</div>)}
          </motion.div>
        </Float>
      ))}
    </div>
  )
}

export default function Overview({ go }) {
  const { data, error } = useApi('overview')
  if (error) return <p className="error-text">{error}</p>
  if (!data) return <div className="stack"><Loading height={280} /><Loading height={200} /></div>
  const { totals, outcomes, activity, model } = data
  const by = totals.students_by_source

  return (
    <>
      <PageHead title="Overview" sub="Everything in the database at a glance. Open University and ASSISTments records are real, anonymised data." />

      <section className="hero" style={{ marginBottom: 20 }}>
        <div className="hero-copy">
          <p style={{ color: 'var(--on-slate-2)' }}>Students on record</p>
          <div className="hero-num">{fmt(totals.students)}</div>
          <p style={{ marginTop: 14, color: 'var(--on-slate-2)', maxWidth: 420 }}>
            {fmt(by.oulad || 0)} from the Open University, {fmt(by.assistments || 0)} from ASSISTments and {fmt(by.local || 0)} added here,
            across {fmt(totals.courses)} courses and {fmt(totals.enrollments)} enrollments.
          </p>
          <div className="row" style={{ marginTop: 22 }}>
            <Button onClick={() => go('students')}>Open students</Button>
            <Button kind="quiet" onClick={() => go('ask')} style={{ color: 'var(--brass-hi)' }}>Ask the data</Button>
          </div>
        </div>
        <HeroCards totals={totals} />
      </section>

      <div className="split-wide" style={{ marginBottom: 20 }}>
        <div className="card card-pad">
          <div className="card-head">
            <div>
              <h2 className="card-title">How Open University courses ended</h2>
              <p className="card-sub">Share who passed, failed or withdrew in each presentation, 2013–14.</p>
            </div>
          </div>
          <StackedBars labelWidth={120} rowHeight={20}
            rows={outcomes.map((o) => ({ label: o.code, parts: { Pass: o.completed, Fail: o.failed, Withdrawn: o.withdrawn } }))} />
        </div>
        <div className="stack" style={{ gap: 20 }}>
          <div className="card card-pad">
            <h2 className="card-title">Activity predicts the result</h2>
            <p className="card-sub" style={{ marginBottom: 14 }}>Average days with any study, by final result.</p>
            <Bars data={activity.map((a) => ({ label: a.result, value: a.avg_active_days }))} unit=" days" labelWidth={110} />
          </div>
          {model && (
            <TiltCard className="card-pad" max={5} onClick={() => go('risk')} style={{ cursor: 'pointer' }}>
              <h2 className="card-title">At-risk model</h2>
              <p className="card-sub">Trained on 2013 students, tested on {fmt(model.n_test)} snapshots of 2014 students it never saw.</p>
              <div className="row" style={{ gap: 28, marginTop: 16 }}>
                {[['ROC AUC', model.roc_auc], ['Precision', model.precision], ['Recall', model.recall]].map(([k, v]) => (
                  <div key={k}>
                    <div className="stat-label">{k}</div>
                    <div className="stat-value" style={{ fontSize: 32 }}>{fmt(v, 2)}</div>
                  </div>
                ))}
              </div>
            </TiltCard>
          )}
        </div>
      </div>

      <div className="stat-row">
        <Stat label="Enrollments" value={fmt(totals.enrollments)} note={`${fmt(totals.active)} still active`} />
        <Stat label="Completion rate" value={pct(totals.completion_rate, 1)} note="of enrollments that have ended" />
        <Stat label="Certificates" value={fmt(totals.certificates)} note="issued, not revoked" />
        <Stat label="Answers logged" value={fmt(totals.answers)} note={`on ${fmt(totals.questions)} live questions`} />
      </div>
    </>
  )
}
