import { Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button, Confirm, FormDialog, Loading, PageHead, Pill, Table } from '../components/ui'
import { api, useApi } from '../lib/api'
import { dateText } from '../lib/format'

const ROLE_TONE = { admin: 'brass', instructor: 'good', student: undefined }

export default function Accounts({ session }) {
  const { data, reload } = useApi('users', {}, [])
  const [adding, setAdding] = useState(false)
  const [resetting, setResetting] = useState(null)
  const [removing, setRemoving] = useState(null)
  return (
    <>
      <PageHead title="Accounts"
        actions={<Button icon={Plus} onClick={() => setAdding(true)}>Add instructor</Button>} />
      {data ? (
        <Table rows={data} columns={[
          { key: 'username', label: 'Username', render: (r) => <b>{r.username}</b> },
          { key: 'name', label: 'Name' },
          { key: 'role', label: 'Role', render: (r) => <Pill tone={ROLE_TONE[r.role]}>{r.role}</Pill> },
          { key: 'last_login_at', label: 'Last sign-in', render: (r) => (r.last_login_at ? `${dateText(r.last_login_at)} ${r.last_login_at.slice(11, 16)}` : 'Never') },
          { key: 'id', label: '', render: (r) => (r.id === session.user_id ? null : (
            <span className="row" style={{ gap: 6 }}>
              <Button kind="secondary" size="sm" onClick={() => setResetting(r)}>Reset password</Button>
              <Button kind="quiet" size="sm" onClick={() => setRemoving(r)}>Remove</Button>
            </span>
          )) },
        ]} />
      ) : <Loading height={240} />}
      <FormDialog open={adding} onClose={() => setAdding(false)} title="Add an instructor"
        fields={[['name', 'Full name'], ['email', 'Email', 'email', 'Optional'], ['username', 'Username'], ['password', 'Password', 'password', '8 or more characters']]}
        submit={(v) => api('instructor_add', { name: v.name || '', email: v.email || '', username: v.username || '', password: v.password || '' })}
        onDone={(v) => { toast.success(`${v.name} can now sign in as ${v.username}`); reload() }} />
      <FormDialog open={!!resetting} onClose={() => setResetting(null)} title={`New password for ${resetting?.username ?? ''}`}
        fields={[['password', 'New password', 'password', '8 or more characters']]}
        submit={(v) => api('password_reset', { user_id: resetting.id, password: v.password || '' })}
        onDone={() => toast.success('Password reset')} />
      <Confirm open={!!removing} onClose={() => setRemoving(null)} title={`Remove ${removing?.username ?? ''}?`}
        text="They can no longer sign in. Their records and results stay."
        onConfirm={async () => { try { await api('user_remove', { user_id: removing.id }); toast.success('Account removed'); reload() } catch (e) { toast.error(e.message) } }} />
    </>
  )
}
