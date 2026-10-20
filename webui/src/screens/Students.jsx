import { KeyRound, Pencil, Plus, Trash2, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { CoachNotes, MasterySkyline, StudyCalendar } from '../components/learning'
import { Button, Confirm, Dialog, Empty, Field, Loading, PageHead, Pill, SearchInput, Select, Sheet, Table, Tabs } from '../components/ui'
import { api } from '../lib/api'
import { dateText, fmt, initials, plural, sourceText, statusText, statusTone } from '../lib/format'
import { useApi, useDebounced } from '../lib/useApi'

const SOURCES = [
  { value: '', label: 'All students' }, { value: 'local', label: 'Added here' },
  { value: 'oulad', label: 'Open University' }, { value: 'assistments', label: 'ASSISTments' },
]
const PAGE = 60

export function StudentForm({ open, onClose, student, onSaved }) {
  const [form, setForm] = useState({})
  const [error, setError] = useState('')
  useEffect(() => {
    if (open) {
      setForm({ name: student?.display_name || '', email: student?.email || '', region: student?.region || '', education: student?.highest_education || '' })
      setError('')
    }
  }, [open, student])
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const save = async () => {
    try {
      const id = await api('student_save', { ...form, student_id: student?.id })
      toast.success(student ? 'Student saved' : `Added ${form.name.trim()}`)
      onSaved(id)
      onClose()
    } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={onClose} title={student ? 'Edit student' : 'Add a student'}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>{student ? 'Save changes' : 'Add student'}</Button></>}>
      <Field label="Full name">{(id) => <input id={id} className="input" autoFocus value={form.name || ''} onChange={set('name')} />}</Field>
      <Field label="Email" hint="Optional">{(id) => <input id={id} className="input" type="email" value={form.email || ''} onChange={set('email')} />}</Field>
      <div className="split" style={{ gap: 14 }}>
        <Field label="Region or city">{(id) => <input id={id} className="input" value={form.region || ''} onChange={set('region')} />}</Field>
        <Field label="Education">{(id) => <input id={id} className="input" value={form.education || ''} onChange={set('education')} />}</Field>
      </div>
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

function LoginForm({ open, onClose, student, onSaved }) {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  useEffect(() => { if (open) { setForm({ username: (student?.display_name || '').split(' ')[0].toLowerCase(), password: '' }); setError('') } }, [open, student])
  const save = async () => {
    try {
      await api('student_create_login', { student_id: student.id, ...form })
      toast.success(`${student.display_name} can now sign in as ${form.username.trim()}`)
      onSaved()
      onClose()
    } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={onClose} title="Create a login" intro={`Lets ${student?.display_name} sign in and study on their own.`}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>Create login</Button></>}>
      <Field label="Username">{(id) => <input id={id} className="input" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />}</Field>
      <Field label="Password" hint="8 or more characters">{(id) => <input id={id} className="input" type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} />}</Field>
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

function Profile({ id, go, onChanged, onRemoved }) {
  const { data, reload } = useApi('student_profile', { student_id: id }, [id])
  const [tab, setTab] = useState('Courses')
  const [mastery, setMastery] = useState(null)
  const [calendar, setCalendar] = useState(null)
  const [editing, setEditing] = useState(false)
  const [login, setLogin] = useState(false)
  const [removing, setRemoving] = useState(false)
  useEffect(() => { setMastery(null); setCalendar(null) }, [id])

  if (!data) return <div className="stack"><Loading height={90} /><Loading height={220} /></div>
  const s = data.student
  const local = s.source === 'local'
  const facts = [['Email', s.email], ['Region', s.region], ['Education', s.highest_education], ['Age band', s.age_band],
    ['Deprivation band', s.imd_band], ['Disability', { Y: 'Yes', N: 'No' }[s.disability] || s.disability]].filter(([, v]) => v)
  const tiles = mastery?.tiles || data.mastery
  const cal = calendar || data.calendar

  return (
    <div className="stack" style={{ gap: 22 }}>
      <div className="row" style={{ gap: 16 }}>
        <span className="avatar" style={{ width: 54, height: 54, fontSize: 18, background: 'var(--slate)' }} aria-hidden>{initials(s.display_name)}</span>
        <div>
          <div className="row" style={{ gap: 8 }}>
            <Pill tone={local ? 'brass' : undefined}>{sourceText[s.source]}</Pill>
            {s.external_id && <span className="xsmall faint">Dataset ID {s.external_id}</span>}
            {data.has_login && <Pill tone="good">Has a login</Pill>}
          </div>
          <div className="row wrap" style={{ gap: 8, marginTop: 10 }}>
            <Button kind="secondary" size="sm" icon={Pencil} onClick={() => setEditing(true)}>Edit</Button>
            {local && <Button kind="secondary" size="sm" icon={UserRound} onClick={() => go('learn', { studentId: s.id })}>Learner view</Button>}
            {local && !data.has_login && <Button kind="secondary" size="sm" icon={KeyRound} onClick={() => setLogin(true)}>Create login</Button>}
            <Button kind="danger" size="sm" icon={Trash2} onClick={() => setRemoving(true)}>Remove</Button>
          </div>
        </div>
      </div>

      {facts.length > 0 && (
        <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 24px', margin: 0 }}>
          {facts.map(([k, v]) => (
            <div key={k}><dt className="xsmall faint" style={{ fontWeight: 700 }}>{k}</dt><dd style={{ margin: 0 }}>{v}</dd></div>
          ))}
        </dl>
      )}

      <Tabs id="profile" value={tab} onChange={setTab} items={['Courses', 'Mastery', 'Study days', 'Coach']} />

      {tab === 'Courses' && (
        data.enrollments.length ? (
          <div className="stack" style={{ gap: 8 }}>
            {data.enrollments.map((e) => {
              const score = e.source === 'oulad' ? e.weighted_score : e.avg_score
              return (
                <div key={e.id} className="card" style={{ padding: '12px 16px', boxShadow: 'none' }}>
                  <div className="row" style={{ justifyContent: 'space-between' }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700 }}>{e.title}</div>
                      <div className="xsmall faint">{e.code} · {e.modules_done} of {e.modules_total} modules{e.enrolled_on ? ` · since ${dateText(e.enrolled_on)}` : ''}</div>
                    </div>
                    <div className="row">
                      {score !== null && <span className="read num" style={{ fontSize: 20 }}>{fmt(score)}%</span>}
                      <Pill tone={statusTone[e.status]} dot>{e.final_result || statusText[e.status]}</Pill>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : <Empty title="No courses yet">Enroll this student from the Enrollments screen.</Empty>
      )}

      {tab === 'Mastery' && (
        data.enrollments.length ? (
          <div className="stack">
            <Select label="Course" value={mastery?.course ?? data.mastery_course}
              options={data.enrollments.map((e) => ({ value: e.course_id, label: e.title }))}
              onChange={async (v) => setMastery({ course: Number(v), tiles: await api('student_mastery', { student_id: id, course_id: Number(v) }) })} />
            <p className="xsmall faint">Block height is mastery. Recent answers count more than old ones.</p>
            <MasterySkyline tiles={tiles} />
          </div>
        ) : <Empty title="Nothing to measure yet" />
      )}

      {tab === 'Study days' && (
        <div className="stack">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <p className="small muted">{plural(data.streaks.active_days, 'active day')} · longest streak {plural(data.streaks.longest, 'day')} · last active {dateText(data.streaks.last_active)}</p>
            {cal.years.length > 1 && (
              <Select label="Year" value={cal.year} options={cal.years.map((y) => ({ value: y, label: String(y) }))}
                onChange={async (y) => setCalendar(await api('student_calendar', { student_id: id, year: Number(y) }))} width={110} />
            )}
          </div>
          <StudyCalendar year={cal.year} days={cal.days} />
        </div>
      )}

      {tab === 'Coach' && <CoachNotes notes={data.notes} />}

      <StudentForm open={editing} onClose={() => setEditing(false)} student={s} onSaved={() => { reload(); onChanged() }} />
      <LoginForm open={login} onClose={() => setLogin(false)} student={s} onSaved={reload} />
      <Confirm open={removing} onClose={() => setRemoving(false)} title="Remove this student?" action="Remove student"
        text={`This deletes ${s.display_name} with their enrollments, answers, progress and certificates. It can't be undone.`}
        onConfirm={async () => { await api('student_remove', { student_id: s.id }); toast.success(`Removed ${s.display_name}`); onRemoved() }} />
    </div>
  )
}

export default function Students({ go, params }) {
  const [text, setText] = useState('')
  const [source, setSource] = useState('')
  const [offset, setOffset] = useState(0)
  const [open, setOpen] = useState(null)
  const [adding, setAdding] = useState(!!params?.add)
  const q = useDebounced(text)
  useEffect(() => setOffset(0), [q, source])
  const { data, reload } = useApi('students_search', { text: q, source, offset, limit: PAGE }, [q, source, offset])
  const openRow = data?.rows.find((r) => r.id === open)

  return (
    <>
      <PageHead title="Students" sub="Search, add and update students. Pick one to see their record."
        actions={<Button icon={Plus} onClick={() => setAdding(true)}>Add student</Button>} />
      <div className="row" style={{ marginBottom: 14 }}>
        <SearchInput value={text} onChange={setText} placeholder="Search by name, email or dataset ID" width={340} />
        <Select label="Source" value={source} onChange={setSource} options={SOURCES} width={190} />
        <span className="spacer" />
        {data && <span className="small muted num">{fmt(data.total)} students</span>}
      </div>
      {data ? (
        <Table rows={data.rows} total={data.total} offset={offset} pageSize={PAGE} onPage={setOffset} selectedKey={open}
          onRowClick={(r) => setOpen(r.id)}
          empty={<Empty title="No students match">Try a shorter search, or another source.</Empty>}
          columns={[
            { key: 'display_name', label: 'Name', render: (r) => <span className="row" style={{ gap: 10 }}><span className="avatar" style={{ width: 28, height: 28, fontSize: 11, background: 'var(--slate-2)' }} aria-hidden>{initials(r.display_name)}</span>{r.display_name}</span> },
            { key: 'source', label: 'Source', render: (r) => sourceText[r.source] },
            { key: 'region', label: 'Region' },
            { key: 'highest_education', label: 'Education' },
            { key: 'courses', label: 'Courses', align: 'r' },
          ]} />
      ) : <Loading height={420} />}

      <Sheet open={!!open} onClose={() => setOpen(null)} title={openRow?.display_name || 'Student'}
        subtitle={openRow ? `${openRow.courses} course${openRow.courses === 1 ? '' : 's'}` : undefined}>
        {open && <Profile id={open} go={go} onChanged={reload} onRemoved={() => { setOpen(null); reload() }} />}
      </Sheet>
      <StudentForm open={adding} onClose={() => setAdding(false)} onSaved={(id) => { setSource('local'); setText(''); reload(); setOpen(id) }} />
    </>
  )
}
