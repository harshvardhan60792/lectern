import { Check, Lock } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button, Empty, Loading, PageHead, Pill } from '../components/ui'
import { api } from '../lib/api'
import { fmt } from '../lib/format'
import { useApi } from '../lib/useApi'

/**
 * The card-catalog drawer. Each course is an index card standing in the drawer;
 * hovering lifts it, picking it pulls it up out of the drawer to read.
 */
function Drawer({ courses, picked, onPick }) {
  const reduce = useReducedMotion()
  const [hover, setHover] = useState(null)
  const n = courses.length
  const STEP = 100 // how much of each card behind shows above the one in front
  const LIFT = 96 // how far the picked card rises out of the drawer
  return (
    <div className="drawer">
      <div className="drawer-cards" style={{ height: 300 + (n - 1) * STEP + LIFT }}>
        {courses.map((c, i) => {
          const depth = n - 1 - i // cards further back stand higher, so their tops show
          const isPicked = picked === c.id
          const isHover = hover === c.id && !isPicked
          return (
            <motion.button
              key={c.id}
              className="index-card"
              aria-pressed={isPicked}
              aria-label={`${c.title}${c.status ? `, ${c.status}` : ''}`}
              onClick={() => onPick(c.id)}
              onPointerEnter={() => setHover(c.id)}
              onPointerLeave={() => setHover(null)}
              onFocus={() => setHover(c.id)}
              onBlur={() => setHover(null)}
              style={{ zIndex: i + 1 }}
              initial={reduce ? false : { y: 200, rotateX: -35 }}
              animate={{
                y: -depth * STEP - (isPicked ? LIFT : isHover ? 26 : 0),
                rotateX: isPicked ? 0 : isHover ? -3 : -7,
                scale: 1 - depth * 0.03,
                filter: picked && !isPicked ? 'brightness(0.94)' : 'brightness(1)',
              }}
              transition={{ type: 'spring', stiffness: 240, damping: 24, delay: reduce ? 0 : 0.06 * i }}
            >
              <span className="ic-tab" style={{ left: 24 + i * 170 }}>{c.code}</span>
              <span className="ic-code" style={{ display: 'block' }}>{c.subject}</span>
              <span className="ic-title" style={{ display: 'block' }}>{c.title}</span>
              <span className="ic-body" style={{ display: 'block' }}>
                {c.modules} modules · {fmt(c.lessons)} lessons · {fmt(c.questions)} questions
                {c.status === 'active' && ' · You are enrolled'}
                {c.status === 'completed' && ' · Completed'}
                {c.missing.length > 0 && ` · Unlocks after ${c.missing.join(', ')}`}
              </span>
            </motion.button>
          )
        })}
      </div>
      <div className="drawer-front"><span className="drawer-label">Courses open for enrollment</span></div>
    </div>
  )
}

export default function Catalog({ session, params, go }) {
  const sid = session.role === 'student' ? session.student_id : params.studentId
  const { data, reload } = useApi(sid ? 'catalog' : null, { student_id: sid }, [sid])
  const [picked, setPicked] = useState(null)
  useEffect(() => { if (data?.length && !picked) setPicked(data[0].id) }, [data, picked])
  if (!sid) return <Empty title="For students">This page lists courses a student can join.</Empty>
  if (!data) return <Loading height={500} />
  const c = data.find((x) => x.id === picked)

  const enroll = async () => {
    try {
      await api('enroll', { student_id: sid, course_id: c.id })
      toast.success(`Enrolled in ${c.title}`)
      reload()
      go('learn', params)
    } catch (e) { toast.error(e.message) }
  }

  return (
    <>
      <PageHead title="Browse courses" sub="Pull a card from the drawer to read about the course. Some courses unlock only after you finish another one." />
      {data.length === 0 ? <Empty title="No open courses yet" /> : (
        <div className="split" style={{ gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 1fr)', alignItems: 'start' }}>
          <Drawer courses={data} picked={picked} onPick={setPicked} />
          <AnimatePresence mode="wait">
            {c && (
              <motion.section key={c.id} className="card card-pad stack" style={{ gap: 16, transformPerspective: 1200 }}
                initial={{ opacity: 0, x: 30, rotateY: -10 }} animate={{ opacity: 1, x: 0, rotateY: 0 }} exit={{ opacity: 0, x: -10, transition: { duration: 0.12 } }}
                transition={{ type: 'spring', stiffness: 220, damping: 24 }}>
                <div>
                  <div className="xsmall" style={{ fontWeight: 700, color: 'var(--brass-ink)' }}>{c.code} · {c.subject}</div>
                  <h2 className="read" style={{ fontSize: 32, fontWeight: 500, lineHeight: 1.15, marginTop: 4 }}>{c.title}</h2>
                </div>
                <p className="read" style={{ fontSize: 18, lineHeight: 1.6 }}>{c.description}</p>
                <div className="row wrap">
                  <Pill>{c.modules} modules</Pill><Pill>{fmt(c.lessons)} lessons</Pill><Pill>{fmt(c.questions)} quiz questions</Pill><Pill>Pass mark {c.pass_mark ?? 50}%</Pill>
                </div>
                {c.requires.length > 0 && (
                  <p className="small" style={{ color: c.missing.length ? 'var(--amber)' : 'var(--ink-2)' }}>
                    {c.missing.length ? <Lock size={14} aria-hidden style={{ verticalAlign: -2, marginRight: 6 }} /> : null}
                    Requires {c.requires.map((r) => r.title).join(', ')}{c.missing.length ? '. Finish it first.' : ' (done).'}
                  </p>
                )}
                <div className="row">
                  {c.status === 'active' || c.status === 'completed' ? (
                    <Pill tone="good"><Check size={12} aria-hidden />{c.status === 'active' ? 'You are enrolled' : 'Completed'}</Pill>
                  ) : (
                    <Button onClick={enroll} disabled={c.missing.length > 0}>Enroll in this course</Button>
                  )}
                </div>
                {c.attribution && <p className="xsmall faint">{c.attribution}</p>}
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      )}
    </>
  )
}
