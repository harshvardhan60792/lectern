import { KeyRound, Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button, Dialog, Field, Loading, PageHead, Pill, Table } from '../components/ui'
import { api } from '../lib/api'
import { dateText } from '../lib/format'
import { useApi } from '../lib/useApi'

const ROLE_TONE = { admin: 'brass', instructor: 'good', student: undefined }

function FormDialog({ open, onClose, title, fields, submit, onDone }) {
  const [values, setValues] = useState({})
  const [error, setError] = useState('')
  const save = async () => {
    try { await submit(values); onDone(values); setValues({}); onClose() } catch (e) { setError(e.message) }
  }
  return (
    <Dialog open={open} onClose={() => { setError(''); onClose() }} title={title}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button onClick={save}>Save</Button></>}>
      {fields.map(([key, label, type, hint]) => (
        <Field key={key} label={label} hint={hint}>{(id) => (
          <input id={id} className="input" type={type || 'text'} autoComplete={type === 'password' ? 'new-password' : 'off'}
            value={values[key] || ''} onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))} />
        )}</Field>
      ))}
      <div role="status" className="error-text">{error}</div>
    </Dialog>
  )
}

export default function Accounts() {
  const { data, reload } = useApi('users', {}, [])
  const [adding, setAdding] = useState(false)
  const [changing, setChanging] = useState(false)
  return (
    <>
      <PageHead title="Accounts" sub="Who can sign in. Student logins are created from a student's record on the Students screen."
        actions={<>
          <Button kind="secondary" icon={KeyRound} onClick={() => setChanging(true)}>Change my password</Button>
          <Button icon={Plus} onClick={() => setAdding(true)}>Add instructor</Button>
        </>} />
      {data ? (
        <Table rows={data} columns={[
          { key: 'username', label: 'Username', render: (r) => <b>{r.username}</b> },
          { key: 'name', label: 'Name' },
          { key: 'role', label: 'Role', render: (r) => <Pill tone={ROLE_TONE[r.role]}>{r.role}</Pill> },
          { key: 'last_login_at', label: 'Last sign-in', render: (r) => (r.last_login_at ? `${dateText(r.last_login_at)} ${r.last_login_at.slice(11, 16)}` : 'Never') },
        ]} />
      ) : <Loading height={240} />}
      <FormDialog open={adding} onClose={() => setAdding(false)} title="Add an instructor"
        fields={[['name', 'Full name'], ['email', 'Email', 'email', 'Optional'], ['username', 'Username'], ['password', 'Password', 'password', '8 or more characters']]}
        submit={(v) => api('instructor_add', { name: v.name || '', email: v.email || '', username: v.username || '', password: v.password || '' })}
        onDone={(v) => { toast.success(`${v.name} can now sign in as ${v.username}`); reload() }} />
      <FormDialog open={changing} onClose={() => setChanging(false)} title="Change password"
        fields={[['old', 'Current password', 'password'], ['new', 'New password', 'password', '8 or more characters'], ['repeat', 'Repeat new password', 'password']]}
        submit={(v) => api('password_change', { old: v.old || '', new: v.new || '', repeat: v.repeat || '' })}
        onDone={() => toast.success('Password changed')} />
    </>
  )
}
