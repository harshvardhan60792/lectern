import { ArrowLeft, ArrowRight, Award, BookOpen, Check, CirclePlay, Layers, RotateCcw, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Float, TiltCard } from '../components/depth'
import { CoachNotes, MasterySkyline, StudyCalendar } from '../components/learning'
import { Button, Empty, Loading, PageHead, Pill } from '../components/ui'
import { api } from '../lib/api'
import { dateText, fmt, masteryTone, plural } from '../lib/format'
import { spring } from '../lib/motion'
import { useApi } from '../lib/useApi'

const LETTERS = 'ABCDE'

function Progress({ value, height = 6 }) {
  return (
    <div style={{ height, borderRadius: height, background: 'var(--line-soft)', overflow: 'hidden' }} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <motion.div style={{ height: '100%', background: 'linear-gradient(90deg, var(--green), color-mix(in srgb, var(--green) 70%, var(--brass)))', originX: 0 }}
        initial={{ scaleX: 0 }} animate={{ scaleX: value / 100 }} transition={{ duration: 0.8, ease: [0.2, 0.8, 0.2, 1] }} />
    </div>
  )
}

/* ---------------- Home ---------------- */

function ReviewDeck({ review, onStart }) {
  const n = Math.min(review.due, 4)
  return (
    <div className="card card-pad" style={{ overflow: 'hidden' }}>
      <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
        <div style={{ position: 'relative', width: 120, height: 92, perspective: 700, flex: 'none' }} aria-hidden>
          {Array.from({ length: Math.max(1, n) }).map((_, i) => (
            <Float key={i} delay={i * 0.4} distance={4} rotate={0.6} style={{ position: 'absolute', left: i * 7, top: 14 - i * 5 }}>
              <div style={{ width: 92, height: 62, borderRadius: 3, transform: `rotate(${(i - 1) * 4}deg)`, boxShadow: 'var(--shadow-paper)',
                background: 'linear-gradient(180deg, transparent 0 16px, rgba(174,58,42,.5) 16px 17px, transparent 17px), repeating-linear-gradient(180deg, transparent 0 11px, rgba(46,107,71,.15) 11px 12px), #F8F8F1',
                opacity: review.due ? 1 : 0.5 }} />
            </Float>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          <h2 className="card-title">Mistakes to review</h2>
          <p className="read" style={{ fontSize: 40, lineHeight: 1.1, margin: '4px 0' }}>{review.due}</p>
          <p className="small muted">{review.due ? 'ready to try again today' : review.next_due ? `Next ones come back on ${dateText(review.next_due)}.` : 'Wrong answers will wait here for a second try.'}</p>
          <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(4, auto)', justifyContent: 'start', gap: '0 18px', margin: '10px 0 0' }}>
            {[['Back tomorrow', 1], ['In 3 days', 2], ['In 7 days', 3], ['Learned', 4]].map(([label, box]) => (
              <div key={box}><dt className="xsmall faint">{label}</dt><dd className="read num" style={{ margin: 0, fontSize: 18 }}>{review.boxes[box]}</dd></div>
            ))}
          </dl>
        </div>
      </div>
      {review.due > 0 && <div style={{ marginTop: 16 }}><Button icon={Layers} onClick={onStart}>Start review</Button></div>}
    </div>
  )
}

function WeekPlan({ plan }) {
  const busy = plan.filter((d) => d.tasks.length)
  if (!busy.length) return <p className="small muted">No tasks yet. Enroll in a course to get a plan.</p>
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${plan.length}, minmax(120px, 1fr))`, gap: 10, overflowX: 'auto' }}>
      {plan.map((d, i) => (
        <motion.div key={d.date} initial={{ opacity: 0, y: 12, rotateX: -25 }} animate={{ opacity: 1, y: 0, rotateX: 0 }}
          transition={{ ...spring, delay: i * 0.05 }} className="card" style={{ padding: '12px 12px', boxShadow: 'none', background: i === 0 ? 'var(--brass-soft)' : 'var(--card-2)', transformPerspective: 700 }}>
          <div style={{ fontWeight: 700, fontSize: 'var(--fs-sm)' }}>{i === 0 ? 'Today' : d.weekday}</div>
          <div className="xsmall faint" style={{ marginBottom: 8 }}>{dateText(d.date)}</div>
          {d.tasks.length ? d.tasks.map((t) => <p key={t} className="xsmall" style={{ marginBottom: 6, lineHeight: 1.4 }}>{t}</p>) : <p className="xsmall faint">Rest</p>}
        </motion.div>
      ))}
    </div>
  )
}

function Home({ sid, staff, openCourse, startQuiz, go }) {
  const { data, reload } = useApi('learn_home', { student_id: sid }, [sid])
  if (!data) return <div className="stack"><Loading height={120} /><Loading height={300} /></div>
  const first = data.student.display_name.split(' ')[0]
  const s = data.streaks
  return (
    <>
      <PageHead title={`Hello, ${first}`}
        sub={`${staff ? `Viewing as ${data.student.display_name}. ` : ''}${new Date(`${data.today}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}. ${s.current ? `${s.current}-day study streak.` : 'Study today to start a streak.'}`}
        actions={staff && <Button kind="secondary" icon={ArrowLeft} onClick={() => go('students')}>Back to students</Button>} />

      <div className="split" style={{ marginBottom: 20 }}>
        <ReviewDeck review={data.review} onStart={() => startQuiz({ review: true })} />
        <div className="card card-pad">
          <h2 className="card-title">Coach notes</h2>
          <p className="card-sub" style={{ marginBottom: 14 }}>Written by rules from your own results.</p>
          <CoachNotes notes={data.notes} />
        </div>
      </div>

      <section style={{ marginBottom: 20 }}>
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="card-title">Your courses</h2>
          {!staff && <Button kind="quiet" onClick={() => go('catalog')}>Browse courses</Button>}
        </div>
        {data.active.length === 0 ? (
          <div className="card"><Empty title="Nothing in progress" action={!staff && <Button onClick={() => go('catalog')}>Browse courses</Button>}>Pick a course to start. Your plan and coach notes fill in as you go.</Empty></div>
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {data.active.map((e) => (
              <TiltCard key={e.course_id} className="card-pad" max={5} onClick={() => openCourse(e.course_id)} style={{ cursor: 'pointer' }}
                role="button" tabIndex={0} aria-label={`Continue ${e.title}`} onKeyDown={(ev) => ev.key === 'Enter' && openCourse(e.course_id)}>
                <div className="xsmall" style={{ fontWeight: 700, color: 'var(--brass-ink)' }}>{e.code}</div>
                <h3 className="read" style={{ fontWeight: 500, fontSize: 22, margin: '4px 0 14px' }}>{e.title}</h3>
                <Progress value={e.progress.percent} />
                <p className="xsmall muted" style={{ marginTop: 8 }}>{e.progress.modules_done} of {e.progress.modules_total} modules · {e.progress.lessons_done} of {e.progress.lessons_total} lessons read</p>
                <p className="small" style={{ marginTop: 10 }}>{e.pace.text}</p>
                <div className="row" style={{ marginTop: 14 }}><Button size="sm" icon={ArrowRight}>Continue</Button></div>
              </TiltCard>
            ))}
          </div>
        )}
      </section>

      {data.active[0] && (
        <section className="card card-pad" style={{ marginBottom: 20 }}>
          <h2 className="card-title">Mastery · {data.active[0].title}</h2>
          <p className="card-sub">Block height is how well you know each module. Recent answers count more.</p>
          <MasterySkyline tiles={data.active[0].mastery} />
        </section>
      )}

      <section className="card card-pad" style={{ marginBottom: 20 }}>
        <h2 className="card-title" style={{ marginBottom: 14 }}>This week</h2>
        <WeekPlan plan={data.plan} />
      </section>

      <div className="split-wide">
        <section className="card card-pad">
          <h2 className="card-title">Study days</h2>
          <p className="card-sub" style={{ marginBottom: 12 }}>{plural(s.active_days, 'day')} with study · longest streak {plural(s.longest, 'day')}</p>
          <StudyCalendar year={data.calendar.year} days={data.calendar.days} />
        </section>
        <section className="card card-pad">
          <h2 className="card-title">Recommended next</h2>
          <div className="stack" style={{ marginTop: 12, gap: 14 }}>
            {data.recommendations.length === 0 && <p className="small muted">Nothing new to suggest right now.</p>}
            {data.recommendations.map((r) => (
              <div key={r.course_id}>
                <div style={{ fontWeight: 700 }}>{r.title}</div>
                <p className="xsmall muted" style={{ margin: '2px 0 6px' }}>{r.reason}</p>
                {!r.locked && <Button kind="secondary" size="sm" onClick={async () => { try { await api('enroll', { student_id: sid, course_id: r.course_id }); toast.success(`Enrolled in ${r.title}`); reload() } catch (e) { toast.error(e.message) } }}>Enroll</Button>}
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  )
}

/* ---------------- Course ---------------- */

function Course({ sid, courseId, back, openLesson, startQuiz }) {
  const { data } = useApi('learn_course', { student_id: sid, course_id: courseId }, [courseId])
  const [open, setOpen] = useState(null)
  if (!data) return <Loading height={400} />
  return (
    <>
      <PageHead title={data.course.title} sub={`${data.progress.modules_done} of ${data.progress.modules_total} modules passed · pass mark ${data.course.pass_mark}% · ${data.pace.text}`}
        actions={<Button kind="secondary" icon={ArrowLeft} onClick={back}>My learning</Button>} />
      <div style={{ marginBottom: 20 }}><Progress value={data.progress.percent} height={8} /></div>
      <div className="stack" style={{ gap: 12 }}>
        {data.modules.map((m, i) => {
          const t = m.mastery
          const isOpen = open === m.id
          const read = m.lessons_list.filter((l) => l.done).length
          return (
            <motion.div key={m.id} layout className="card" initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}>
              <div className="row" style={{ padding: '16px 20px', gap: 16, cursor: 'pointer' }} onClick={() => setOpen(isOpen ? null : m.id)}
                role="button" tabIndex={0} aria-expanded={isOpen} onKeyDown={(e) => e.key === 'Enter' && setOpen(isOpen ? null : m.id)}>
                <div className="read num" style={{ fontSize: 28, width: 36, color: 'var(--ink-3)' }}>{m.position}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="read" style={{ fontSize: 20 }}>{m.title.replace(/^\d+\.\s*/, '')}</div>
                  <div className="xsmall faint">{read} of {m.lessons} lessons read · {fmt(m.questions)} questions in the bank</div>
                </div>
                {t?.completed && <Pill tone="good"><Check size={12} aria-hidden />Passed</Pill>}
                {t?.mastery !== null && t?.mastery !== undefined && <Pill tone={masteryTone(t.mastery)}>Mastery {t.mastery}%</Pill>}
                {m.questions > 0 && <Button size="sm" kind="secondary" onClick={(e) => { e.stopPropagation(); startQuiz({ moduleId: m.id, back: courseId }) }}>Take quiz</Button>}
              </div>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0, transition: { duration: 0.15 } }}
                    transition={{ type: 'spring', stiffness: 280, damping: 30 }} style={{ overflow: 'hidden' }}>
                    <div style={{ padding: '0 20px 16px 72px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 6 }}>
                      {m.lessons_list.map((l) => (
                        <button key={l.id} className="btn btn-quiet" style={{ justifyContent: 'flex-start', color: l.done ? 'var(--green)' : 'var(--ink)', fontWeight: 600 }}
                          onClick={() => openLesson(l.id)}>
                          {l.done ? <Check size={15} aria-label="Read" /> : <BookOpen size={15} aria-hidden />}{l.title}
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </>
  )
}

/* ---------------- Lesson ---------------- */

function Lesson({ sid, lessonId, back, openLesson }) {
  const { data } = useApi('lesson', { lesson_id: lessonId }, [lessonId])
  const siblings = useApi(data ? 'learn_course' : null, { student_id: sid, course_id: data?.course_id }, [data?.course_id])
  if (!data) return <Loading height={500} />
  const list = siblings.data?.modules.find((m) => m.id === data.module_id)?.lessons_list || []
  const idx = list.findIndex((l) => l.id === lessonId)
  const next = list[idx + 1]
  const prev = list[idx - 1]
  const finish = async () => {
    await api('lesson_complete', { student_id: sid, lesson_id: lessonId })
    if (next) openLesson(next.id)
    else { toast.success('Module read. Try its quiz.'); back() }
  }
  return (
    <div className="reader">
      <div className="row" style={{ marginBottom: 18 }}>
        <Button kind="secondary" size="sm" icon={ArrowLeft} onClick={back}>Course</Button>
        <span className="small faint">{data.course_title} · {data.module_title}</span>
      </div>
      <motion.article key={lessonId} initial={{ opacity: 0, rotateY: 8, x: 30 }} animate={{ opacity: 1, rotateY: 0, x: 0 }} transition={{ type: 'spring', stiffness: 200, damping: 26 }}
        className="card" style={{ padding: '44px 56px', transformPerspective: 1400, transformOrigin: '0% 50%' }}>
        <h1 className="read" style={{ fontSize: 40, fontWeight: 500, lineHeight: 1.1, marginBottom: 22 }}>{data.title}</h1>
        {data.video_url && (
          <div style={{ marginBottom: 22 }}><Button kind="secondary" icon={CirclePlay} onClick={() => api('open_url', { url: data.video_url })}>Watch the video</Button></div>
        )}
        <div className="reader-text">
          {data.blocks.map((b, i) => (b.type === 'code' ? <pre key={i} className="code">{b.text}</pre> : b.type === 'heading' ? <h3 key={i}>{b.text}</h3> : <p key={i}>{b.text}</p>))}
        </div>
        {data.attribution && <p className="xsmall faint" style={{ marginTop: 24 }}>{data.attribution}</p>}
      </motion.article>
      <div className="row" style={{ marginTop: 18 }}>
        {prev && <Button kind="secondary" icon={ArrowLeft} onClick={() => openLesson(prev.id)}>Previous lesson</Button>}
        <span className="spacer" />
        <Button icon={next ? ArrowRight : Check} onClick={finish}>{next ? 'Mark as read and continue' : 'Mark as read'}</Button>
      </div>
    </div>
  )
}

/* ---------------- Quiz ---------------- */

function Quiz({ sid, spec, done }) {
  const reduce = useReducedMotion()
  const [attempt, setAttempt] = useState(null)
  const [i, setI] = useState(0)
  const [dir, setDir] = useState(1)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const start = spec.review ? api('review_start', { student_id: sid }) : api('quiz_start', { student_id: sid, module_id: spec.moduleId })
    start.then(setAttempt).catch((e) => setError(e.message))
  }, [sid, spec])

  if (error) return <Empty title="Can't start" action={<Button onClick={done}>Back</Button>}>{error}</Empty>
  if (!attempt) return <Loading height={400} />
  if (result) return <Result result={result} done={done} />

  const qs = attempt.questions
  const q = qs[i]
  const [first, ...code] = q.prompt.split('\n')
  const go = (step) => { setDir(step); setI((x) => x + step) }
  const unanswered = qs.filter((x) => !answers[x.id]).length
  // Every question is sent; a skipped one goes as null and counts as wrong.
  const submit = async () => setResult(await api('quiz_submit', {
    attempt_id: attempt.attempt_id,
    answers: Object.fromEntries(qs.map((x) => [x.id, answers[x.id] ?? null])),
  }))

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <div className="row" style={{ marginBottom: 14 }}>
        <span className="small muted">{attempt.kind === 'review' ? 'Review' : 'Quiz'} · question {i + 1} of {qs.length}</span>
        <span className="spacer" />
        <Button kind="quiet" size="sm" icon={X} onClick={done}>Leave</Button>
      </div>
      <div className="row" style={{ gap: 4, marginBottom: 22 }}>
        {qs.map((x, k) => (
          <span key={x.id} style={{ flex: 1, height: 5, borderRadius: 3, background: k === i ? 'var(--brass)' : answers[x.id] ? 'var(--green)' : 'var(--line)', transition: 'background .2s' }} />
        ))}
      </div>
      <div className="quiz-stage">
        {/* the next card peeks out underneath, like a deck */}
        {i + 1 < qs.length && !reduce && <div className="card" aria-hidden style={{ position: 'absolute', inset: '14px 14px -14px', opacity: 0.6, transform: 'rotate(1.2deg)' }} />}
        <AnimatePresence mode="popLayout" custom={dir} initial={false}>
          <motion.div key={q.id} custom={dir} className="card question-card"
            variants={{
              in: (d) => ({ opacity: 0, x: d * 90, rotateY: d * -14, rotateZ: d * 2 }),
              show: { opacity: 1, x: 0, rotateY: 0, rotateZ: 0 },
              out: (d) => ({ opacity: 0, x: d * -120, rotateY: d * 16, rotateZ: d * -3, transition: { duration: 0.18 } }),
            }}
            initial="in" animate="show" exit="out" transition={{ type: 'spring', stiffness: 260, damping: 26 }} style={{ transformPerspective: 1400 }}>
            <p className="question-text">{first}</p>
            {code.length > 0 && <pre className="code" style={{ marginTop: 14 }}>{code.join('\n')}</pre>}
            <div className="stack" role="radiogroup" aria-label="Answers" style={{ gap: 10, marginTop: 22 }}>
              {q.options.map((o, k) => (
                <button key={o.id} role="radio" aria-checked={answers[q.id] === o.id} className="option"
                  onClick={() => setAnswers((a) => ({ ...a, [q.id]: o.id }))}>
                  <span className="letter">{LETTERS[k]}</span><span className="opt-text">{o.text}</span>
                </button>
              ))}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="row" style={{ marginTop: 22 }}>
        {i > 0 && <Button kind="secondary" icon={ArrowLeft} onClick={() => go(-1)}>Back</Button>}
        <span className="spacer" />
        {i + 1 < qs.length ? <Button icon={ArrowRight} onClick={() => go(1)}>Next</Button> : (
          <>
            {unanswered > 0 && <span className="small" style={{ color: 'var(--amber)' }}>{unanswered} unanswered</span>}
            <Button icon={Check} onClick={submit}>Submit answers</Button>
          </>
        )}
      </div>
    </div>
  )
}

function Result({ result, done }) {
  const tone = result.score >= 75 ? 'green' : result.score >= 50 ? 'amber' : 'red'
  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <motion.div className="card card-pad row" style={{ gap: 28, marginBottom: 20 }} initial={{ opacity: 0, scale: 0.96, rotateX: 18 }}
        animate={{ opacity: 1, scale: 1, rotateX: 0 }} transition={{ type: 'spring', stiffness: 200, damping: 20 }}>
        <motion.div className="read num" style={{ fontSize: 88, lineHeight: 1, color: `var(--${tone})` }} initial={{ scale: 0.6 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 220, damping: 12, delay: 0.15 }}>
          {fmt(result.score)}%
        </motion.div>
        <div>
          <h2 className="card-title">{result.correct} of {result.total} right</h2>
          <p className="small muted" style={{ marginTop: 4 }}>{result.kind === 'review' ? 'Right answers move to a longer gap. Wrong ones come back tomorrow.' : 'Wrong answers go to your review queue and come back tomorrow.'}</p>
        </div>
      </motion.div>
      {result.certificate && (
        <motion.div className="card card-pad row" style={{ gap: 16, marginBottom: 20, background: 'var(--brass-soft)' }}
          initial={{ opacity: 0, rotateY: -90 }} animate={{ opacity: 1, rotateY: 0 }} transition={{ type: 'spring', stiffness: 120, damping: 16, delay: 0.4 }}>
          <Award size={40} color="var(--brass-ink)" aria-hidden />
          <div>
            <h3 className="read" style={{ fontWeight: 500, fontSize: 24 }}>Course complete. Your certificate is ready.</h3>
            <p className="small">Code {result.certificate.code}. Find it under Certificates.</p>
          </div>
        </motion.div>
      )}
      <div className="stack" style={{ gap: 10 }}>
        {result.feedback.map((f, i) => {
          const [first, ...code] = f.prompt.split('\n')
          return (
            <motion.div key={f.question_id} className="card card-pad" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + i * 0.04 }}>
              <div className="row" style={{ alignItems: 'flex-start', gap: 14 }}>
                <Pill tone={f.correct ? 'good' : 'bad'}>{f.correct ? <Check size={12} aria-hidden /> : <X size={12} aria-hidden />}{f.correct ? 'Right' : f.chosen_option_id == null ? 'Skipped' : 'Wrong'}</Pill>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p>{first}</p>
                  {code.length > 0 && <pre className="code" style={{ marginTop: 8 }}>{code.join('\n')}</pre>}
                  {!f.correct && <p className="small" style={{ color: 'var(--green)', marginTop: 6, whiteSpace: 'pre-wrap' }}>Answer: {f.right_answer}</p>}
                  {f.explanation && <p className="small muted" style={{ marginTop: 4 }}>{f.explanation}</p>}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
      <div className="row" style={{ marginTop: 20 }}><Button icon={RotateCcw} onClick={done}>Done</Button></div>
    </div>
  )
}

/* ---------------- Screen ---------------- */

export default function Learn({ session, params, go }) {
  const staff = session.role !== 'student'
  const sid = staff ? params.studentId : session.student_id
  const [view, setView] = useState({ name: 'home' })
  const [stamp, setStamp] = useState(0)
  const show = (v) => { setView(v); setStamp((s) => s + 1) }

  if (staff && !sid) return <Empty title="Pick a student first">Open a student added here on the Students screen, then choose Learner view.</Empty>

  return (
    <AnimatePresence mode="wait">
      <motion.div key={`${view.name}-${stamp}`} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16, transition: { duration: 0.12 } }} transition={{ duration: 0.25 }}>
        {view.name === 'home' && <Home sid={sid} staff={staff} go={go} openCourse={(id) => show({ name: 'course', id })}
          startQuiz={(spec) => show({ name: 'quiz', spec })} />}
        {view.name === 'course' && <Course sid={sid} courseId={view.id} back={() => show({ name: 'home' })}
          openLesson={(lid) => show({ name: 'lesson', id: lid, course: view.id })} startQuiz={(spec) => show({ name: 'quiz', spec })} />}
        {view.name === 'lesson' && <Lesson sid={sid} lessonId={view.id} back={() => show({ name: 'course', id: view.course })}
          openLesson={(lid) => show({ name: 'lesson', id: lid, course: view.course })} />}
        {view.name === 'quiz' && <Quiz sid={sid} spec={view.spec} done={() => show(view.spec.back ? { name: 'course', id: view.spec.back } : { name: 'home' })} />}
      </motion.div>
    </AnimatePresence>
  )
}
