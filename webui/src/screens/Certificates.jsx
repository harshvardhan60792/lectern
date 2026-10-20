import { FileDown, RotateCcw, ShieldCheck, ShieldX } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { FlipCard } from '../components/depth'
import { Button, Confirm, Empty, Field, Loading, PageHead, Pill, SearchInput, Table } from '../components/ui'
import { api, useApi, useDebounced } from '../lib/api'
import { dateText, fmt } from '../lib/format'

/** The certificate itself. Turn it over to see the fingerprint that makes it tamper-evident. */
function Certificate({ code }) {
  const { data } = useApi('certificate_verify', { code }, [code])
  const [flipped, setFlipped] = useState(false)
  useEffect(() => setFlipped(false), [code])
  if (!data) return <Loading height={380} />
  const c = data.certificate
  return (
    <div className="stack">
      <FlipCard flipped={flipped} height={380}
        front={(
          <div className="cert-face">
            <p style={{ fontWeight: 700, color: '#7A5714', fontSize: 14 }}>Lectern · Certificate of completion</p>
            <p style={{ marginTop: 26, fontSize: 15 }}>This certifies that</p>
            <p className="cert-name">{c.student_name}</p>
            <p style={{ fontSize: 15 }}>has completed</p>
            <p className="read" style={{ fontSize: 22, marginTop: 6, maxWidth: 420 }}>{c.course_title}</p>
            <p style={{ fontSize: 14, marginTop: 22 }}>Issued {dateText(c.issued_on)}{c.score !== null ? ` · final score ${fmt(c.score, 1)}%` : ''}{c.grade ? ` · ${c.grade}` : ''}</p>
            <p style={{ fontSize: 12, marginTop: 6, color: '#5A5A4A' }}>Code {c.code}</p>
            <div className="cert-seal" aria-hidden>L</div>
          </div>
        )}
        back={(
          <div className="cert-face cert-back">
            <p style={{ fontWeight: 700, color: '#E2BC6A', fontSize: 14 }}>How this certificate proves itself</p>
            <p style={{ marginTop: 16, fontSize: 15, lineHeight: 1.6, maxWidth: 460 }}>
              When it was issued, Lectern hashed the code, name, course, date and score with SHA-256. Change any one character and the hash comes out completely different.
            </p>
            <p style={{ marginTop: 18, fontSize: 13, color: '#A9B6AC' }}>Fingerprint</p>
            <p className="fingerprint">{c.fingerprint}</p>
            <p className="row" style={{ marginTop: 18, gap: 8, color: data.valid ? '#7DBB91' : '#EE8A78', fontWeight: 700 }}>
              {data.valid ? <ShieldCheck size={18} aria-hidden /> : <ShieldX size={18} aria-hidden />}{data.reason}
            </p>
          </div>
        )} />
      <div className="row">
        <Button kind="secondary" icon={RotateCcw} onClick={() => setFlipped((f) => !f)}>{flipped ? 'Show the front' : 'Turn it over'}</Button>
        <Button kind="secondary" icon={FileDown} onClick={async () => { try { await api('certificate_pdf', { code: c.code }); toast.success('PDF saved to exports/certificates') } catch (e) { toast.error(e.message) } }}>Save PDF</Button>
      </div>
    </div>
  )
}

function Verify() {
  const [f, setF] = useState({ code: '', student_name: '', course_title: '', issued_on: '', score: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const run = async (e) => {
    e.preventDefault()
    setError('')
    try { setResult(await api('certificate_verify', f)) } catch (err) { setError(err.message); setResult(null) }
  }
  return (
    <form className="card card-pad stack" onSubmit={run}>
      <div>
        <h2 className="card-title">Verify a certificate</h2>
        <p className="card-sub">Enter the code. To check a PDF someone sent you, also type the details printed on it.</p>
      </div>
      <Field label="Code">{(id) => <input id={id} className="input" placeholder="LEC-3E77-4731" value={f.code} onChange={set('code')} />}</Field>
      <div className="split" style={{ gap: 12 }}>
        <Field label="Name on the PDF">{(id) => <input id={id} className="input" value={f.student_name} onChange={set('student_name')} />}</Field>
        <Field label="Score on the PDF">{(id) => <input id={id} className="input" inputMode="decimal" value={f.score} onChange={set('score')} />}</Field>
      </div>
      <div className="split" style={{ gap: 12 }}>
        <Field label="Course on the PDF">{(id) => <input id={id} className="input" value={f.course_title} onChange={set('course_title')} />}</Field>
        <Field label="Issue date (YYYY-MM-DD)">{(id) => <input id={id} className="input" value={f.issued_on} onChange={set('issued_on')} />}</Field>
      </div>
      <div className="row"><Button type="submit" disabled={!f.code.trim()}>Verify</Button></div>
      <div role="status" aria-live="polite">
        {error && <p className="error-text">{error}</p>}
        <AnimatePresence mode="wait">
          {result && (
            <motion.div key={result.reason + result.valid} initial={{ opacity: 0, scale: 0.97, rotateX: -20 }} animate={{ opacity: 1, scale: 1, rotateX: 0 }}
              exit={{ opacity: 0, transition: { duration: 0.1 } }} transition={{ type: 'spring', stiffness: 300, damping: 22 }}
              className="row" style={{ gap: 12, padding: '14px 16px', borderRadius: 8, background: result.valid ? 'var(--green-soft)' : 'var(--red-soft)', transformPerspective: 800 }}>
              {result.valid ? <ShieldCheck size={28} color="var(--green)" aria-hidden /> : <ShieldX size={28} color="var(--red)" aria-hidden />}
              <div>
                <div className="read" style={{ fontSize: 22, color: result.valid ? 'var(--green)' : 'var(--red)' }}>{result.valid ? 'Genuine' : 'Not valid'}</div>
                <div className="small">{result.reason}</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </form>
  )
}

export default function Certificates({ session }) {
  const [text, setText] = useState('')
  const q = useDebounced(text)
  const [offset, setOffset] = useState(0)
  const [picked, setPicked] = useState(null)
  const [revoking, setRevoking] = useState(false)
  useEffect(() => setOffset(0), [q])
  const { data, reload } = useApi('certificates_list', { text: q, offset, limit: 60 }, [q, offset])
  const student = session.role === 'student'
  return (
    <>
      <PageHead title="Certificates" sub="Each certificate carries a SHA-256 fingerprint of its details. Change the name, course, date or score and verification fails." />
      <div className="split" style={{ alignItems: 'start' }}>
        <div className="stack">
          {!student && <SearchInput value={text} onChange={setText} placeholder="Search code, student or course" width={340} />}
          {data ? (
            <Table rowKey="code" rows={data.rows} total={student ? undefined : data.total} offset={offset} pageSize={60} onPage={student ? undefined : setOffset}
              onRowClick={(r) => setPicked(r.code)} selectedKey={picked} maxHeight="calc(100vh - 300px)"
              empty={<Empty title="No certificates yet">They're issued automatically when a course is completed.</Empty>}
              columns={[
                { key: 'code', label: 'Code' },
                ...(student ? [] : [{ key: 'student', label: 'Student' }]),
                { key: 'course_title', label: 'Course', render: (r) => <span style={{ display: 'block', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.course_title}</span> },
                { key: 'issued_on', label: 'Issued', render: (r) => dateText(r.issued_on) },
                { key: 'revoked', label: '', render: (r) => (r.revoked ? <Pill tone="bad">Revoked</Pill> : null) },
              ]} />
          ) : <Loading height={400} />}
        </div>
        <div className="stack" style={{ gap: 20 }}>
          {picked ? (
            <>
              <Certificate code={picked} />
              {session.role === 'admin' && <div><Button kind="danger" size="sm" onClick={() => setRevoking(true)}>Revoke this certificate</Button></div>}
            </>
          ) : <div className="card"><Empty title="Pick a certificate">See it, turn it over to read its fingerprint, or save it as a PDF.</Empty></div>}
          <Verify />
        </div>
      </div>
      <Confirm open={revoking} onClose={() => setRevoking(false)} title="Revoke this certificate?" action="Revoke"
        text={`${picked} will no longer verify.`} onConfirm={async () => { await api('certificate_revoke', { code: picked }); toast.success('Revoked'); reload(); setPicked(null) }} />
    </>
  )
}
