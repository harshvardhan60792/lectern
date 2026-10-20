import { ArrowDown, ArrowUp, BookOpenText, ChevronRight, Pencil, Plus, Trash2, Video } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Histogram, Lines } from '../components/charts'
import { TiltCard } from '../components/depth'
import { CourseMap } from '../components/learning'
import { Button, Confirm, Dialog, Empty, Field, Loading, PageHead, Pill, SearchInput, Select, Sheet, Table, Tabs } from '../components/ui'
import { api, useApi, useDebounced } from '../lib/api'
import { fmt, sourceText } from '../lib/format'

const FILTERS = [
  { value: '', label: 'All courses' }, { value: 'local', label: 'Created here' }, { value: 'openstax', label: 'Programming' },
  { value: 'sciq', label: 'Science' }, { value: 'assistments', label: 'Maths practice' }, { value: 'oulad', label: 'Past courses' },
]

/** A small ring showing completion; the number is written inside, so colour isn't needed to read it. */
function Ring({ value }) {
  const r = 20, c = 2 * Math.PI * r
  const v = value ?? 0
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" style={{ flex: "none" }} aria-label={value === null ? 'No results yet' : `${value}% completed`}>
      <circle cx="28" cy="28" r={r} fill="none" stroke="var(--line)" strokeWidth="5" />
      {value !== null && (
        <motion.circle cx="28" cy="28" r={r} fill="none" stroke="var(--green)" strokeWidth="5" strokeLinecap="round"
          transform="rotate(-90 28 28)" strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - v / 100) }}
          transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }} />
      )}
      <text x="28" y="32" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--ink)">{value === null ? '—' : `${Math.round(v)}%`}</text>
    </svg>
  )
}

function CourseForm({ open, onClose, course, instructors = [], onSaved }) {
  const [f, setF] = useState({})
  const [error, setError] = useState('')
  useEffect(() => {
    if (open) {
      setF({ code: course?.code || '', title: course?.title || '', subject: course?.subject || '', description: course?.description || '',
        pass_mark: course?.pass_mark ?? 50, instructor_id: course?.instructor_id ?? '' })
      setError('')
    }
  }, [open, course])
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const save = async () => {
    try {
      const id = await api('course_save', { ...f, instructor_id: f.instructor_id ? Number(f.instructor_id) : null, course_id: course?.id })
      toast.success(course ? 'Course saved' : 'Course created. Add its modules next.')
      onSaved(id)
      onClose()
    } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={onClose} title={course ? 'Edit course' : 'New course'}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>{course ? 'Save changes' : 'Create course'}</Button></>}>
      <div className="split" style={{ gap: 14, gridTemplateColumns: '140px 1fr' }}>
        <Field label="Code" hint="e.g. WEB-101">{(id) => <input id={id} className="input" autoFocus value={f.code || ''} onChange={set('code')} />}</Field>
        <Field label="Title">{(id) => <input id={id} className="input" value={f.title || ''} onChange={set('title')} />}</Field>
      </div>
      <div className="split" style={{ gap: 14, gridTemplateColumns: '1fr 140px' }}>
        <Field label="Subject">{(id) => <input id={id} className="input" value={f.subject || ''} onChange={set('subject')} />}</Field>
        <Field label="Pass mark (%)">{(id) => <input id={id} className="input" inputMode="numeric" value={f.pass_mark} onChange={set('pass_mark')} />}</Field>
      </div>
      <Field label="Description">{(id) => <textarea id={id} className="textarea" value={f.description || ''} onChange={set('description')} />}</Field>
      <Field label="Instructor">{(id) => (
        <select id={id} className="select" value={f.instructor_id ?? ''} onChange={set('instructor_id')}>
          <option value="">Nobody yet</option>
          {instructors.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
      )}</Field>
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

function LessonEditor({ open, onClose, moduleId, lesson, onSaved }) {
  const [f, setF] = useState({ title: '', video_url: '', body: '' })
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    setError('')
    if (lesson) api('lesson', { lesson_id: lesson.id }).then((l) => setF({ title: l.title, video_url: l.video_url || '', body: l.body }))
    else setF({ title: '', video_url: '', body: '' })
  }, [open, lesson])
  const save = async () => {
    try {
      await api('lesson_save', { module_id: moduleId, lesson_id: lesson?.id, ...f })
      toast.success('Lesson saved')
      onSaved()
      onClose()
    } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={onClose} title={lesson ? 'Edit lesson' : 'Add a lesson'}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>Save lesson</Button></>}>
      <Field label="Title">{(id) => <input id={id} className="input" value={f.title} onChange={(e) => setF((x) => ({ ...x, title: e.target.value }))} />}</Field>
      <Field label="Video link" hint="Optional. Starts with https://">{(id) => <input id={id} className="input" value={f.video_url} onChange={(e) => setF((x) => ({ ...x, video_url: e.target.value }))} />}</Field>
      <Field label="Lesson text">{(id) => <textarea id={id} className="textarea" style={{ minHeight: 220 }} value={f.body} onChange={(e) => setF((x) => ({ ...x, body: e.target.value }))} />}</Field>
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

function LessonPreview({ lessonId, onClose }) {
  const { data } = useApi('lesson', { lesson_id: lessonId }, [lessonId])
  return (
    <Dialog open={!!lessonId} onClose={onClose} title={data?.title || 'Lesson'} footer={<Button onClick={onClose}>Done</Button>}>
      {!data ? <Loading /> : (
        <div className="reader-text" style={{ fontSize: 16, maxHeight: '55vh', overflowY: 'auto', paddingRight: 8 }}>
          {data.blocks.map((b, i) => (b.type === 'code' ? <pre key={i} className="code">{b.text}</pre> : b.type === 'heading' ? <h3 key={i}>{b.text}</h3> : <p key={i}>{b.text}</p>))}
        </div>
      )}
    </Dialog>
  )
}

function ModulesTab({ detail, reload }) {
  const c = detail.course
  const editable = !c.historical
  const [openModule, setOpenModule] = useState(null)
  const [lessons, setLessons] = useState({})
  const [naming, setNaming] = useState(null)
  const [title, setTitle] = useState('')
  const [lessonEdit, setLessonEdit] = useState(null)
  const [preview, setPreview] = useState(null)
  const [removing, setRemoving] = useState(null)

  const refreshLessons = async (id) => {
    const rows = await api('lessons', { module_id: id })
    setLessons((l) => ({ ...l, [id]: rows }))
  }
  const toggle = (id) => {
    if (openModule === id) return setOpenModule(null)
    setOpenModule(id)
    if (!lessons[id]) refreshLessons(id)
  }

  const saveName = async () => {
    try {
      if (naming === 'new') await api('module_add', { course_id: c.id, title })
      else await api('module_rename', { module_id: naming, title })
      setNaming(null)
      reload()
    } catch (e) { toast.error(e.message) }
  }

  return (
    <div className="stack" style={{ gap: 10 }}>
      {editable && (
        <div className="row"><Button size="sm" icon={Plus} onClick={() => { setTitle(''); setNaming('new') }}>Add module</Button></div>
      )}
      {detail.modules.length === 0 && <Empty title="No modules yet">Add the first module, then put lessons and questions in it.</Empty>}
      {detail.modules.map((m, i) => (
        <motion.div key={m.id} layout className="card" style={{ boxShadow: 'none', overflow: 'hidden' }}>
          <div className="row" style={{ padding: '10px 12px', gap: 10 }}>
            <button className="icon-btn" style={{ border: 0, background: 'none' }} onClick={() => toggle(m.id)} aria-expanded={openModule === m.id} aria-label={`Show lessons of ${m.title}`}>
              <motion.span animate={{ rotate: openModule === m.id ? 90 : 0 }} style={{ display: 'inline-flex' }}><ChevronRight size={17} /></motion.span>
            </button>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700 }}>{m.title}</div>
              <div className="xsmall faint">{m.lessons} lessons · {fmt(m.questions)} questions{m.weight ? ` · weight ${m.weight}%` : ''}</div>
            </div>
            {editable && (
              <div className="row" style={{ gap: 4 }}>
                <button className="icon-btn" disabled={i === 0} aria-label="Move up" onClick={async () => { await api('module_move', { module_id: m.id, direction: -1 }); reload() }}><ArrowUp size={15} /></button>
                <button className="icon-btn" disabled={i === detail.modules.length - 1} aria-label="Move down" onClick={async () => { await api('module_move', { module_id: m.id, direction: 1 }); reload() }}><ArrowDown size={15} /></button>
                <button className="icon-btn" aria-label="Rename" onClick={() => { setTitle(m.title); setNaming(m.id) }}><Pencil size={15} /></button>
                <button className="icon-btn" aria-label="Remove module" onClick={() => setRemoving(m)}><Trash2 size={15} /></button>
              </div>
            )}
          </div>
          <AnimatePresence initial={false}>
            {openModule === m.id && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0, transition: { duration: 0.15 } }}
                transition={{ type: 'spring', stiffness: 300, damping: 32 }} style={{ overflow: 'hidden' }}>
                <div style={{ padding: '0 14px 14px 54px' }} className="stack">
                  {lessons[m.id] === undefined || lessons[m.id] === null ? <Loading height={60} /> : lessons[m.id].length === 0 ? (
                    <p className="small muted">No lessons in this module.</p>
                  ) : lessons[m.id].map((l) => (
                    <div key={l.id} className="row" style={{ gap: 10 }}>
                      <BookOpenText size={15} className="faint" aria-hidden />
                      <button className="btn btn-quiet btn-sm" style={{ color: 'var(--ink)', fontWeight: 600 }} onClick={() => setPreview(l.id)}>{l.title}</button>
                      {l.video_url && <Video size={14} className="faint" aria-label="Has a video" />}
                      <span className="spacer" />
                      {editable && <>
                        <button className="icon-btn" aria-label="Edit lesson" onClick={() => setLessonEdit({ moduleId: m.id, lesson: l })}><Pencil size={14} /></button>
                        <button className="icon-btn" aria-label="Remove lesson" onClick={async () => { await api('lesson_remove', { lesson_id: l.id }); refreshLessons(m.id); reload() }}><Trash2 size={14} /></button>
                      </>}
                    </div>
                  ))}
                  {editable && <div><Button kind="secondary" size="sm" icon={Plus} onClick={() => setLessonEdit({ moduleId: m.id, lesson: null })}>Add lesson</Button></div>}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}

      <Dialog open={naming !== null} onClose={() => setNaming(null)} title={naming === 'new' ? 'Add a module' : 'Rename module'}
        footer={<><Button kind="secondary" onClick={() => setNaming(null)}>Cancel</Button><Button onClick={saveName}>Save</Button></>}>
        <Field label="Module title">{(id) => <input id={id} className="input" autoFocus value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && saveName()} />}</Field>
      </Dialog>
      <LessonEditor open={!!lessonEdit} onClose={() => setLessonEdit(null)} moduleId={lessonEdit?.moduleId} lesson={lessonEdit?.lesson}
        onSaved={() => { refreshLessons(lessonEdit.moduleId); reload() }} />
      <LessonPreview lessonId={preview} onClose={() => setPreview(null)} />
      <Confirm open={!!removing} onClose={() => setRemoving(null)} title="Remove this module?" action="Remove module"
        text={`Removes “${removing?.title}” with its lessons and questions.`}
        onConfirm={async () => { await api('module_remove', { module_id: removing.id }); reload() }} />
    </div>
  )
}

function PrereqTab({ detail, reload, courses }) {
  const c = detail.course
  const graph = useApi('prerequisite_graph', {}, [detail.prerequisites.length])
  const [pick, setPick] = useState('')
  const options = courses.filter((x) => x.id !== c.id && !x.historical && !detail.prerequisites.some((p) => p.id === x.id))
  return (
    <div className="stack" style={{ gap: 16 }}>
      <p className="small muted">Students must complete these first.</p>
      {detail.prerequisites.length ? detail.prerequisites.map((p) => (
        <div key={p.id} className="row card" style={{ padding: '10px 14px', boxShadow: 'none' }}>
          <span className="xsmall" style={{ fontWeight: 700, color: 'var(--brass-ink)' }}>{p.code}</span><span>{p.title}</span>
          <span className="spacer" />
          {!c.historical && <Button kind="danger" size="sm" onClick={async () => { await api('prerequisite_remove', { course_id: c.id, requires_id: p.id }); reload() }}>Remove</Button>}
        </div>
      )) : <p>None. Anyone can enroll.</p>}
      {!c.historical && options.length > 0 && (
        <div className="row">
          <Select label="Course to require" value={pick} onChange={setPick} options={[{ value: '', label: 'Choose a course…' }, ...options.map((o) => ({ value: o.id, label: `${o.code}  ${o.title}` }))]} />
          <Button kind="secondary" disabled={!pick} onClick={async () => {
            try { await api('prerequisite_add', { course_id: c.id, requires_id: Number(pick) }); setPick(''); reload() } catch (e) { toast.error(e.message) }
          }}>Add requirement</Button>
        </div>
      )}
      <h3 className="card-title" style={{ marginTop: 8 }}>Course map</h3>
      {graph.data ? <div style={{ overflowX: 'auto', paddingBottom: 8 }}><CourseMap nodes={graph.data.nodes} edges={graph.data.edges} /></div> : <Loading height={80} />}
    </div>
  )
}

function InsightsTab({ id }) {
  const { data } = useApi('course_insights', { course_id: id }, [id])
  if (!data) return <Loading height={300} />
  const weeks = [...new Set(data.weekly.map((r) => r.week))].sort((a, b) => a - b)
  const series = {}
  ;['Distinction', 'Pass', 'Fail', 'Withdrawn'].forEach((res) => {
    const m = Object.fromEntries(data.weekly.filter((r) => r.result === res).map((r) => [r.week, r.clicks_per_student]))
    if (Object.keys(m).length) series[res] = weeks.map((w) => m[w] || 0)
  })
  const mat = data.materials
  return (
    <div className="stack" style={{ gap: 24 }}>
      <div>
        <h3 className="card-title">Weekly activity by final result</h3>
        <p className="card-sub" style={{ marginBottom: 10 }}>Clicks per student each week, by final result.</p>
        <Lines x={weeks} series={series} xLabel="week of course" yLabel="clicks per student" height={240} />
      </div>
      <div>
        <h3 className="card-title">Course scores</h3>
        <p className="card-sub" style={{ marginBottom: 10 }}>{fmt(data.scores.length)} enrollments. Bars below the pass mark are amber.</p>
        <Histogram values={data.scores} mark={data.pass_mark} markLabel={`Pass mark ${data.pass_mark}%`} xLabel="weighted course score (%)" />
      </div>
      {mat.materials.length > 0 && (
        <div>
          <h3 className="card-title">Materials linked to passing</h3>
          <p className="card-sub" style={{ marginBottom: 10 }}>Overall pass rate {fmt(mat.base_rate * 100)}%. Lift 1.5 means students who used it passed 1.5 times as often. A link, not proof of cause.</p>
          <Table rowKey="material_id" rows={mat.materials} columns={[
            { key: 'label', label: 'Material' },
            { key: 'share', label: 'Used by', align: 'r', render: (r) => `${fmt(r.share * 100)}%` },
            { key: 'pass_rate', label: 'Pass rate', align: 'r', render: (r) => `${fmt(r.pass_rate * 100)}%` },
            { key: 'lift', label: 'Lift', align: 'r', render: (r) => fmt(r.lift, 2) },
          ]} />
        </div>
      )}
    </div>
  )
}

function CourseSheet({ id, onClose, courses, onChanged }) {
  const { data, reload } = useApi('course_detail', { course_id: id }, [id])
  const [tab, setTab] = useState('About')
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  useEffect(() => setTab('About'), [id])
  const refresh = () => { reload(); onChanged() }
  const c = data?.course
  const tabs = ['About', 'Modules', 'Prerequisites', ...(c?.source === 'oulad' ? ['Insights'] : [])]
  return (
    <Sheet open={!!id} onClose={onClose} width="min(760px, calc(100vw - 280px))"
      title={c ? <div><div className="xsmall" style={{ fontWeight: 700, color: 'var(--brass-ink)' }}>{c.code}</div><h2 className="card-title" style={{ fontSize: 'var(--fs-xl)' }}>{c.title}</h2></div> : 'Course'}>
      {!data ? <Loading height={300} /> : (
        <div className="stack" style={{ gap: 20 }}>
          <Tabs id="course" value={tab} onChange={setTab} items={tabs} />
          {tab === 'About' && (
            <div className="stack" style={{ gap: 18 }}>
              <div className="row wrap"><Pill tone={c.source === 'local' ? 'brass' : undefined}>{sourceText[c.source] || c.source}</Pill>{c.archived ? <Pill tone="warn">Archived</Pill> : null}{c.historical && <Pill>Historical record, closed to new students</Pill>}</div>
              {c.description && <p className="read" style={{ fontSize: 18, lineHeight: 1.6, maxWidth: '62ch' }}>{c.description}</p>}
              <div className="stat-row">
                {[['Students', fmt(data.stats.enrolled)], ['Completed', data.stats.completion_rate === null ? '—' : `${fmt(data.stats.completion_rate, 1)}%`],
                  ['Modules', fmt(data.stats.modules)], ['Pass mark', `${c.pass_mark}%`]].map(([k, v]) => (
                  <div key={k}><div className="stat-label">{k}</div><div className="stat-value" style={{ fontSize: 30 }}>{v}</div></div>
                ))}
              </div>
              {!c.historical && (
                <div className="row">
                  <Button kind="secondary" icon={Pencil} onClick={() => setEditing(true)}>Edit details</Button>
                  <Button kind="secondary" onClick={async () => { await api('course_archive', { course_id: c.id, archived: !c.archived }); refresh() }}>{c.archived ? 'Restore' : 'Archive'}</Button>
                  {c.source === 'local' && <Button kind="danger" icon={Trash2} onClick={() => setDeleting(true)}>Delete</Button>}
                </div>
              )}
            </div>
          )}
          {tab === 'Modules' && <ModulesTab detail={data} reload={refresh} />}
          {tab === 'Prerequisites' && <PrereqTab detail={data} reload={refresh} courses={courses} />}
          {tab === 'Insights' && <InsightsTab id={c.id} />}
          <CourseForm open={editing} onClose={() => setEditing(false)} course={c} instructors={data.instructors} onSaved={refresh} />
          <Confirm open={deleting} onClose={() => setDeleting(false)} title="Delete this course?" action="Delete course"
            text="Deletes the course with all its modules, lessons and questions."
            onConfirm={async () => { try { await api('course_remove', { course_id: c.id }); onClose(); onChanged() } catch (e) { toast.error(e.message) } }} />
        </div>
      )}
    </Sheet>
  )
}

export default function Courses({ params }) {
  const [text, setText] = useState('')
  const [source, setSource] = useState('')
  const [archived, setArchived] = useState(false)
  const [open, setOpen] = useState(params?.courseId || null)
  const [adding, setAdding] = useState(!!params?.add)
  const q = useDebounced(text)
  const { data, reload } = useApi('courses_search', { text: q, source, archived }, [q, source, archived])

  return (
    <>
      <PageHead title="Courses"
        actions={<Button icon={Plus} onClick={() => setAdding(true)}>New course</Button>} />
      <div className="row" style={{ marginBottom: 18 }}>
        <SearchInput value={text} onChange={setText} placeholder="Search courses" />
        <Select label="Source" value={source} onChange={setSource} options={FILTERS} width={200} />
        <label className="row small" style={{ gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Show archived
        </label>
      </div>
      {!data ? <Loading height={400} /> : data.length === 0 ? <Empty title="No courses match">Clear the search or pick another source.</Empty> : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))' }}>
          {data.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 12) * 0.03, duration: 0.3 }}>
              <TiltCard className="card-pad" max={6} onClick={() => setOpen(c.id)} style={{ cursor: 'pointer', height: '100%' }}
                role="button" tabIndex={0} aria-label={`Open ${c.title}`} onKeyDown={(e) => e.key === 'Enter' && setOpen(c.id)}>
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="xsmall" style={{ fontWeight: 700, color: 'var(--brass-ink)' }}>{c.code}</div>
                    <h3 className="read" style={{ fontWeight: 500, fontSize: 20, lineHeight: 1.25, marginTop: 4 }}>{c.title}</h3>
                  </div>
                  <Ring value={c.completion_rate} />
                </div>
                <div className="row wrap" style={{ marginTop: 14, gap: 8 }}>
                  <Pill tone={c.source === 'local' ? 'brass' : undefined}>{sourceText[c.source] || c.source}</Pill>
                  <span className="xsmall faint">{fmt(c.enrolled)} student{c.enrolled === 1 ? '' : 's'} · {c.modules} modules</span>
                </div>
              </TiltCard>
            </motion.div>
          ))}
        </div>
      )}
      <CourseSheet id={open} onClose={() => setOpen(null)} courses={data || []} onChanged={reload} />
      <CourseForm open={adding} onClose={() => setAdding(false)} onSaved={(id) => { reload(); setOpen(id) }} />
    </>
  )
}
