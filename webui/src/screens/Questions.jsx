import { Check, Pencil, Plus, RotateCcw, Sparkles } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { FlipCard } from '../components/depth'
import { Button, Dialog, Empty, Field, Loading, PageHead, Pill, SearchInput, Select, Table, Tabs } from '../components/ui'
import { api, useApi, useDebounced } from '../lib/api'
import { fmt } from '../lib/format'

const FLAG_TONE = { Healthy: 'good', 'Too easy': undefined, 'Too hard': 'warn', "Doesn't separate": 'warn', 'Check answer key': 'bad' }
const LETTERS = 'ABCDE'

function QuestionForm({ open, onClose, moduleId, question, onSaved }) {
  const [f, setF] = useState({ prompt: '', options: ['', '', '', ''], correct: 0, explanation: '' })
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    setError('')
    if (question) {
      const opts = question.options.map((o) => o.text)
      while (opts.length < 4) opts.push('')
      setF({ prompt: question.prompt || '', options: opts, correct: Math.max(0, question.options.findIndex((o) => o.is_correct)), explanation: question.explanation || '' })
    } else setF({ prompt: '', options: ['', '', '', ''], correct: 0, explanation: '' })
  }, [open, question])
  const save = async () => {
    try {
      await api('question_save', { module_id: moduleId, question_id: question?.id, status: question?.status || 'live', ...f })
      toast.success(question ? 'Question saved' : 'Question added')
      onSaved()
      onClose()
    } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={onClose} title={question ? 'Edit question' : 'Add a question'}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>Save question</Button></>}>
      <Field label="Question">{(id) => <textarea id={id} className="textarea" style={{ minHeight: 90 }} value={f.prompt} onChange={(e) => setF((x) => ({ ...x, prompt: e.target.value }))} />}</Field>
      <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0, gap: 8 }}>
        <legend className="field-label" style={{ marginBottom: 6 }}>Options (pick the right one)</legend>
        {f.options.map((o, i) => (
          <div key={i} className="row" style={{ gap: 8 }}>
            <input type="radio" name="correct" checked={f.correct === i} onChange={() => setF((x) => ({ ...x, correct: i }))} aria-label={`Option ${LETTERS[i]} is correct`} />
            <input className="input" placeholder={`Option ${LETTERS[i]}${i > 1 ? ' (optional)' : ''}`} value={o}
              onChange={(e) => setF((x) => ({ ...x, options: x.options.map((v, k) => (k === i ? e.target.value : v)) }))} />
          </div>
        ))}
      </fieldset>
      <Field label="Explanation" hint="Optional. Shown after the student answers.">{(id) => <input id={id} className="input" value={f.explanation} onChange={(e) => setF((x) => ({ ...x, explanation: e.target.value }))} />}</Field>
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

function Preview({ id, onEdit, onChanged }) {
  const { data, reload } = useApi('question', { question_id: id }, [id])
  const [flipped, setFlipped] = useState(false)
  useEffect(() => setFlipped(false), [id])
  if (!data) return <Loading height={300} />
  const [first, ...code] = (data.prompt || `ASSISTments problem ${data.external_id}`).split('\n')
  const right = data.options.find((o) => o.is_correct)
  const face = (children) => <div className="card card-pad" style={{ minHeight: 320 }}>{children}</div>
  return (
    <div className="stack">
      <FlipCard flipped={flipped} height={320}
        front={face(<>
          <div className="row" style={{ justifyContent: 'space-between' }}><Pill>{data.source}</Pill><Pill tone={data.status === 'live' ? 'good' : 'warn'}>{data.status}</Pill></div>
          <p className="read" style={{ fontSize: 20, lineHeight: 1.4, margin: '16px 0 10px' }}>{first}</p>
          {code.length > 0 && <pre className="code">{code.join('\n')}</pre>}
          {data.options.length ? (
            <ol className="stack" style={{ gap: 6, paddingLeft: 0, listStyle: 'none', marginTop: 12 }}>
              {data.options.map((o, i) => <li key={o.id} className="small"><b>{LETTERS[i]}.</b> <span style={{ whiteSpace: 'pre-wrap' }}>{o.text}</span></li>)}
            </ol>
          ) : <p className="small muted">This practice set records who answered and whether they were right, not the problem text.</p>}
        </>)}
        back={face(<>
          <p className="small faint">Right answer</p>
          <p className="read" style={{ fontSize: 24, margin: '6px 0 14px', color: 'var(--green)', whiteSpace: 'pre-wrap' }}>{right ? right.text : '—'}</p>
          {data.explanation && <><p className="small faint">Why</p><p style={{ marginTop: 4 }}>{data.explanation}</p></>}
        </>)} />
      <div className="row wrap">
        {data.options.length > 0 && <Button kind="secondary" size="sm" icon={RotateCcw} onClick={() => setFlipped((f) => !f)}>{flipped ? 'Show question' : 'Show answer'}</Button>}
        {data.options.length > 0 && <Button kind="secondary" size="sm" icon={Pencil} onClick={() => onEdit(data)}>Edit</Button>}
        {data.options.length > 0 && (data.status === 'live'
          ? <Button kind="danger" size="sm" onClick={async () => { await api('question_status', { question_id: id, status: 'retired' }); toast('Retired. Students won\'t see it.'); reload(); onChanged() }}>Retire</Button>
          : <Button kind="secondary" size="sm" onClick={async () => { await api('question_status', { question_id: id, status: 'live' }); toast.success('Live again'); reload(); onChanged() }}>Make live</Button>)}
      </div>
    </div>
  )
}

function BankTab({ moduleId, source }) {
  const [text, setText] = useState('')
  const q = useDebounced(text)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(null)
  useEffect(() => { setOffset(0); setSelected(null) }, [moduleId, q])
  const { data, reload } = useApi('question_bank', { module_id: moduleId, text: q, offset, limit: 80 }, [moduleId, q, offset])
  return (
    <div className="split-wide" style={{ alignItems: 'start' }}>
      <div className="stack">
        <div className="row">
          <SearchInput value={text} onChange={setText} placeholder="Search question text" />
          {source !== 'assistments' && <Button kind="secondary" icon={Plus} onClick={() => setForm({ question: null })}>Add question</Button>}
        </div>
        {data ? (
          <Table rows={data.rows} total={data.total} offset={offset} pageSize={80} onPage={setOffset} onRowClick={(r) => setSelected(r.id)} selectedKey={selected}
            maxHeight="calc(100vh - 330px)" empty={<Empty title="No questions in this module yet">Add one, or draft some from the lessons.</Empty>}
            columns={[
              { key: 'prompt', label: 'Question', render: (r) => <span style={{ display: 'block', maxWidth: 460, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{(r.prompt || `Problem ${r.external_id}`).replace(/\n/g, ' ')}</span> },
              { key: 'status', label: 'Status', render: (r) => <Pill tone={r.status === 'live' ? 'good' : 'warn'}>{r.status}</Pill> },
              { key: 'answers', label: 'Answers', align: 'r', render: (r) => fmt(r.answers) },
              { key: 'pct_correct', label: 'Right', align: 'r', render: (r) => (r.pct_correct === null ? '—' : `${r.pct_correct}%`) },
            ]} />
        ) : <Loading height={360} />}
      </div>
      <div style={{ position: 'sticky', top: 0 }}>
        {selected ? <Preview id={selected} onEdit={(question) => setForm({ question })} onChanged={reload} /> : (
          <div className="card"><Empty title="Pick a question">Its preview shows here. Turn the card over to see the answer.</Empty></div>
        )}
      </div>
      <QuestionForm open={!!form} onClose={() => setForm(null)} moduleId={moduleId} question={form?.question} onSaved={() => { reload(); setSelected((s) => s) }} />
    </div>
  )
}

function DraftTab({ moduleId, source }) {
  const [text, setText] = useState('')
  const [count, setCount] = useState('8')
  const [drafts, setDrafts] = useState(null)
  const [keep, setKeep] = useState([])
  const [busy, setBusy] = useState(false)
  if (['assistments', 'oulad'].includes(source)) {
    return <Empty title="No lesson text in this course">The drafter reads lesson text. Pick a textbook, science or self-made course.</Empty>
  }
  const run = async () => {
    setBusy(true)
    try {
      const d = await api('draft_questions', { module_id: moduleId, how_many: Number(count), text })
      setDrafts(d)
      setKeep(d.map(() => true))
      if (!d.length) toast('Not enough clear sentences and key terms. Try a longer passage.')
    } catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  const save = async (status) => {
    const chosen = drafts.filter((_, i) => keep[i])
    const n = await api('save_drafts', { module_id: moduleId, drafts: chosen, status })
    toast.success(`Saved ${n} question${n === 1 ? '' : 's'} as ${status}`)
    setDrafts(null)
  }
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="card card-pad stack">
        <div>
          <h2 className="card-title">Draft questions from text</h2>
          <p className="card-sub">Drafts from this module's lessons, or from text you paste. Check each one before saving.</p>
        </div>
        <textarea className="textarea" style={{ minHeight: 90 }} placeholder="Leave empty to use the module's lessons" value={text} onChange={(e) => setText(e.target.value)} aria-label="Text to draft from" />
        <div className="row">
          <Button icon={Sparkles} onClick={run} disabled={busy}>{busy ? 'Reading the text…' : 'Draft questions'}</Button>
          <Select label="How many" value={count} onChange={setCount} options={['5', '8', '12'].map((v) => ({ value: v, label: `${v} questions` }))} width={150} />
        </div>
      </div>
      <AnimatePresence>
        {drafts?.map((d, i) => (
          <motion.div key={d.sentence + i} className="card card-pad" layout
            initial={{ opacity: 0, x: 40, rotateY: -12 }} animate={{ opacity: keep[i] ? 1 : 0.5, x: 0, rotateY: 0 }} exit={{ opacity: 0, x: -30, transition: { duration: 0.15 } }}
            transition={{ type: 'spring', stiffness: 260, damping: 26, delay: i * 0.05 }} style={{ transformPerspective: 1000 }}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <label className="row small" style={{ gap: 8, cursor: 'pointer', fontWeight: 700 }}>
                <input type="checkbox" checked={keep[i]} onChange={() => setKeep((k) => k.map((v, j) => (j === i ? !v : v)))} /> Keep
              </label>
              <Pill>{d.kind === 'definition' ? 'Definition' : 'Fill in the blank'}</Pill>
            </div>
            <p className="read" style={{ fontSize: 18, margin: '12px 0', whiteSpace: 'pre-wrap' }}>{d.prompt}</p>
            <div className="row wrap" style={{ gap: 8 }}>
              {d.options.map((o, k) => <Pill key={o} tone={k === d.correct ? 'good' : undefined}>{k === d.correct && <Check size={12} aria-label="Right answer" />}{o}</Pill>)}
            </div>
            <p className="xsmall faint" style={{ marginTop: 12 }}>From: “{d.sentence.slice(0, 180)}”</p>
          </motion.div>
        ))}
      </AnimatePresence>
      {drafts?.length > 0 && (
        <div className="row">
          <Button onClick={() => save('live')}>Save kept as live</Button>
          <Button kind="secondary" onClick={() => save('draft')}>Save kept as drafts</Button>
        </div>
      )}
    </div>
  )
}

function HealthTab({ courseId, moduleId }) {
  const [scope, setScope] = useState('course')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [picked, setPicked] = useState(null)
  useEffect(() => { setResult(null); setPicked(null) }, [courseId])
  const run = async () => {
    setBusy(true)
    try { setResult(await api('question_health', { course_id: courseId, module_id: scope === 'module' ? moduleId : null })) }
    catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="card card-pad stack">
        <div>
          <h2 className="card-title">How well do the questions work?</h2>
          <p className="card-sub">Finds questions that are too easy, too hard, or may have the wrong answer marked.</p>
        </div>
        <div className="row">
          <Select label="Scope" value={scope} onChange={setScope} options={[{ value: 'course', label: 'Whole course' }, { value: 'module', label: 'Selected module' }]} width={180} />
          <Button onClick={run} disabled={busy}>{busy ? 'Checking every answer…' : 'Run check'}</Button>
        </div>
      </div>
      {result && (result.items.length === 0 ? (
        <Empty title={`No question has ${result.min_answers}+ answers yet`}>The check needs that many to be reliable. The Maths skill builder course has real answer data.</Empty>
      ) : (
        <>
          <div className="stat-row">
            {['Healthy', 'Too easy', 'Too hard', "Doesn't separate", 'Check answer key'].map((k) => (
              <div key={k} className="card stat">
                <div className="stat-label">{k}</div>
                <div className="stat-value" style={{ color: FLAG_TONE[k] ? `var(--${FLAG_TONE[k] === 'good' ? 'green' : FLAG_TONE[k] === 'warn' ? 'amber' : 'red'})` : undefined }}>{fmt(result.counts[k] || 0)}</div>
              </div>
            ))}
          </div>
          <div className="split-wide" style={{ alignItems: 'start' }}>
            <Table rowKey="question_id" rows={result.items} onRowClick={setPicked} selectedKey={picked?.question_id} maxHeight="52vh"
              columns={[
                { key: 'flag', label: 'Verdict', render: (r) => <Pill tone={FLAG_TONE[r.flag]} dot>{r.flag}</Pill> },
                { key: 'label', label: 'Question', render: (r) => <span style={{ display: 'block', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.label.replace(/\n/g, ' ')}</span> },
                { key: 'answers', label: 'Answers', align: 'r' },
                { key: 'difficulty', label: 'Difficulty', align: 'r', render: (r) => fmt(r.difficulty, 2) },
                { key: 'discrimination', label: 'Discrim.', align: 'r', render: (r) => (r.discrimination === null ? '—' : fmt(r.discrimination, 2)) },
              ]} />
            <div className="card card-pad" style={{ position: 'sticky', top: 0 }}>
              {picked ? (
                <div className="stack">
                  <Pill tone={FLAG_TONE[picked.flag]} dot>{picked.flag}</Pill>
                  <p>{picked.advice}</p>
                  <p className="small muted">{picked.answers} first answers · {fmt(picked.difficulty * 100)}% right · discrimination {picked.discrimination === null ? '—' : fmt(picked.discrimination, 2)} · {picked.module}</p>
                </div>
              ) : <p className="muted small">Pick a row to see what the numbers mean for that question.</p>}
            </div>
          </div>
        </>
      ))}
    </div>
  )
}

export default function Questions() {
  const courses = useApi('courses_search', {}, [])
  const [courseId, setCourseId] = useState('')
  const [moduleId, setModuleId] = useState('')
  const [tab, setTab] = useState('Bank')
  const detail = useApi(courseId ? 'course_detail' : null, { course_id: Number(courseId) }, [courseId])
  useEffect(() => {
    if (courses.data && !courseId) setCourseId(String(courses.data.find((c) => c.code === 'PY-101')?.id || courses.data[0].id))
  }, [courses.data, courseId])
  useEffect(() => {
    if (detail.data?.modules) setModuleId(String(detail.data.modules[0]?.id || ''))
  }, [detail.data])
  const course = detail.data?.course
  const mods = detail.data?.modules || []
  return (
    <>
      <PageHead title="Question bank" />
      <div className="row wrap" style={{ marginBottom: 18 }}>
        <Select label="Course" value={courseId} onChange={(v) => { setCourseId(v); setModuleId('') }} width={340}
          options={(courses.data || []).filter((c) => c.modules && c.source !== 'oulad').map((c) => ({ value: c.id, label: `${c.code}  ${c.title}` }))} />
        <Select label="Module" value={moduleId} onChange={setModuleId} width={300}
          options={mods.map((m) => ({ value: m.id, label: /^\d/.test(m.title) ? m.title : `${m.position}. ${m.title}` }))} />
        <span className="spacer" />
        <Tabs id="qtabs" value={tab} onChange={setTab} items={['Bank', 'Draft from lessons', 'Health check']} />
      </div>
      {!course || !moduleId ? <Loading height={360} /> : (
        <>
          {tab === 'Bank' && <BankTab moduleId={Number(moduleId)} source={course.source} />}
          {tab === 'Draft from lessons' && <DraftTab moduleId={Number(moduleId)} source={course.source} />}
          {tab === 'Health check' && <HealthTab courseId={course.id} moduleId={Number(moduleId)} />}
        </>
      )}
    </>
  )
}
