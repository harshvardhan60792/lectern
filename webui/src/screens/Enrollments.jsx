import { UserMinus, UserPlus } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button, Empty, Loading, PageHead, Pill, SearchInput, Select, Table } from '../components/ui'
import { api, useApi, useDebounced } from '../lib/api'
import { dateText, fmt, initials, sourceText, statusText, statusTone } from '../lib/format'

const STATUS = [
  { value: '', label: 'Any status' }, { value: 'active', label: 'Active' }, { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' }, { value: 'withdrawn', label: 'Withdrawn' },
]
const PAGE = 100

export default function Enrollments() {
  const courses = useApi('courses_search', {}, [])
  const [who, setWho] = useState('')
  const whoQ = useDebounced(who)
  const found = useApi('students_search', { text: whoQ, limit: 8 }, [whoQ])
  const [student, setStudent] = useState(null)
  const [target, setTarget] = useState('')

  const [listCourse, setListCourse] = useState('')
  const [status, setStatus] = useState('')
  const [name, setName] = useState('')
  const nameQ = useDebounced(name)
  const [offset, setOffset] = useState(0)
  useEffect(() => setOffset(0), [listCourse, status, nameQ])
  const roster = useApi(listCourse ? 'course_roster' : null, { course_id: Number(listCourse), status, text: nameQ, offset, limit: PAGE },
    [listCourse, status, nameQ, offset])

  const all = courses.data || []
  const open = all.filter((c) => !c.historical)
  useEffect(() => {
    if (all.length && !listCourse) setListCourse(String(all.find((c) => c.code === 'DDD-2013J')?.id || all[0].id))
    if (open.length && !target) setTarget(String(open[0].id))
  }, [all.length]) // eslint-disable-line react-hooks/exhaustive-deps

  /** The Enroll button: hands the choice to services/enrollments.py `enroll` through the Python bridge. */
  const onEnrollClicked = async () => {
    try {
      await api('enroll', { student_id: student.id, course_id: Number(target) })
      toast.success(`Enrolled ${student.display_name} in ${open.find((c) => c.id === Number(target))?.title}`)
      setListCourse(target)
      roster.reload()
    } catch (e) { toast.error(e.message) }
  }
  const onDropClicked = async () => {
    try {
      await api('drop', { student_id: student.id, course_id: Number(target) })
      toast.success(`Dropped ${student.display_name} from the course`)
      roster.reload()
    } catch (e) { toast.error(e.message) }
  }

  return (
    <>
      <PageHead title="Enrollments" sub="Put students into courses, take them out, and see who is in each course." />
      <div className="split" style={{ gridTemplateColumns: 'minmax(320px, .8fr) minmax(0, 1.4fr)', alignItems: 'start' }}>
        <div className="card card-pad stack" style={{ gap: 16, position: 'sticky', top: 0 }}>
          <div>
            <h2 className="card-title">Enroll a student</h2>
            <p className="card-sub">Find the student, pick a course, then enroll or drop.</p>
          </div>
          <SearchInput value={who} onChange={setWho} placeholder="Type a student's name" width="100%" />
          <div className="stack" style={{ gap: 4, minHeight: 60 }}>
            {whoQ.length < 2 ? <p className="small faint">Type at least two letters.</p> : !found.data ? <Loading height={60} /> :
              found.data.rows.length === 0 ? <p className="small muted">Nobody matches “{whoQ}”.</p> : found.data.rows.map((s) => (
                <button key={s.id} className="row nav-item" style={{ color: 'var(--ink)', background: student?.id === s.id ? 'var(--brass-soft)' : 'none' }}
                  onClick={() => setStudent(s)}>
                  <span className="avatar" style={{ width: 26, height: 26, fontSize: 11, background: 'var(--slate-2)', color: 'var(--on-slate)' }} aria-hidden>{initials(s.display_name)}</span>
                  <span style={{ flex: 1 }}>{s.display_name}</span>
                  <span className="xsmall faint">{sourceText[s.source]}</span>
                </button>
              ))}
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={student?.id || 'none'} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10, transition: { duration: 0.1 } }}
              className="card" style={{ padding: '12px 14px', boxShadow: 'none', background: 'var(--card-2)' }}>
              {student ? <span>Student: <b>{student.display_name}</b></span> : <span className="muted small">No student chosen yet.</span>}
            </motion.div>
          </AnimatePresence>
          <div className="field">
            <span className="field-label">Course</span>
            <Select label="Course to enroll in" value={target} onChange={setTarget} options={open.map((c) => ({ value: c.id, label: `${c.code}  ${c.title}` }))} />
            <span className="xsmall faint">Open University and ASSISTments courses are historical records and closed.</span>
          </div>
          <div className="row">
            <Button icon={UserPlus} disabled={!student || !target} onClick={onEnrollClicked}>Enroll</Button>
            <Button kind="danger" icon={UserMinus} disabled={!student || !target} onClick={onDropClicked}>Drop</Button>
          </div>
        </div>

        <div className="stack">
          <div className="row wrap">
            <Select label="Course" value={listCourse} onChange={setListCourse} options={all.map((c) => ({ value: c.id, label: `${c.code}  ${c.title}` }))} width={340} />
            <Select label="Status" value={status} onChange={setStatus} options={STATUS} width={150} />
            <SearchInput value={name} onChange={setName} placeholder="Name" width={170} />
          </div>
          {roster.data?.rows ? (
            <Table rows={roster.data.rows} total={roster.data.total} offset={offset} pageSize={PAGE} onPage={setOffset} maxHeight="calc(100vh - 290px)"
              empty={<Empty title="Nobody here">No enrollments match these filters.</Empty>}
              columns={[
                { key: 'display_name', label: 'Student' },
                { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone[r.status]} dot>{r.final_result || statusText[r.status]}</Pill> },
                { key: 'enrolled_on', label: 'Enrolled', render: (r) => dateText(r.enrolled_on) },
                { key: 'modules_done', label: 'Modules done', align: 'r' },
                { key: 'avg_score', label: 'Avg score', align: 'r', render: (r) => (r.avg_score === null ? '—' : fmt(r.avg_score, 1)) },
              ]} />
          ) : <Loading height={400} />}
        </div>
      </div>
    </>
  )
}
