import { motion, useReducedMotion } from 'motion/react'
import { useState } from 'react'
import { Button, Field } from '../components/ui'
import { api } from '../lib/api'
import { ease } from '../lib/format'

/** The one orchestrated moment: a book on a lectern turns a page as the app opens. */
function BookScene() {
  const reduce = useReducedMotion()
  return (
    <div className="signin-scene" aria-hidden>
      <motion.div className="lectern"
        initial={reduce ? false : { opacity: 0, transform: 'translateY(30px) rotateX(8deg)' }}
        animate={{ opacity: 1, transform: 'translateY(0px) rotateX(0deg)' }}
        transition={{ duration: 0.9, ease }}>
        <div className="lamp-glow" />
        <div className="lectern-stand" />
        <div className="lectern-desk" />
        <div className="book">
        <motion.div className="book-float" animate={reduce ? undefined : { y: [0, -6, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 1.6 }}>
          <div className="book-page left">
            <h4>Chapter 4</h4>
            {[92, 100, 84, 96, 70, 100, 88, 60, 94, 78, 100, 52].map((w, i) => <div key={i} className="rule" style={{ width: `${w}%` }} />)}
          </div>
          <div className="book-page right">
            <h4>Decisions</h4>
            {[100, 90, 96, 74, 100, 86, 92, 66, 100, 80, 58].map((w, i) => <div key={i} className="rule" style={{ width: `${w}%` }} />)}
          </div>
          {!reduce && [0, 1, 2].map((i) => (
            <motion.div key={i} className="book-page turning"
              initial={{ rotateY: 0 }} animate={{ rotateY: -178 }}
              transition={{ duration: 1.25, delay: 0.7 + i * 0.32, ease: [0.45, 0.05, 0.25, 1] }}>
              {[96, 88, 100, 72, 94, 84, 100, 64, 90].map((w, k) => <div key={k} className="rule" style={{ width: `${w}%` }} />)}
            </motion.div>
          ))}
          <div className="book-spine" />
        </motion.div>
        </div>
      </motion.div>
    </div>
  )
}

export default function SignIn({ state, onSignedIn }) {
  const firstRun = state.db_ready && !state.has_users
  const [form, setForm] = useState({ username: '', password: '', repeat: '' })
  const [error, setError] = useState(state.error ? `Couldn't reach the app's Python side: ${state.error}` : '')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const session = firstRun ? await api('setup_admin', form) : await api('login', form)
      onSignedIn(session)
    } catch (err) {
      setError(err.message)
      setForm((f) => ({ ...f, password: '', repeat: '' }))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="signin">
      <BookScene />
      <div className="signin-panel">
        <motion.div className="signin-box" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.25, ease }}>
          <h1 className="signin-word">Lectern</h1>
          {!state.db_ready ? (
            <div className="stack" style={{ marginTop: 18 }}>
              <p className="muted">The database hasn't been built yet.</p>
              <p className="small">Download the datasets (see <b>docs/database.md</b>), then run <code>python -m db setup</code> in the project folder and open Lectern again.</p>
            </div>
          ) : (
            <>
              <p className="signin-tag">{firstRun ? 'Set up the admin account. It manages students, courses and other accounts.' : 'Courses, progress and certificates in one place.'}</p>
              <form className="stack" style={{ gap: 16 }} onSubmit={submit}>
                <Field label="Username">{(id) => <input id={id} className="input" autoFocus autoComplete="username" value={form.username} onChange={set('username')} />}</Field>
                <Field label="Password" hint={firstRun ? '8 or more characters' : undefined}>
                  {(id) => <input id={id} className="input" type="password" autoComplete={firstRun ? 'new-password' : 'current-password'} value={form.password} onChange={set('password')} />}
                </Field>
                {firstRun && (
                  <Field label="Repeat password">{(id) => <input id={id} className="input" type="password" autoComplete="new-password" value={form.repeat} onChange={set('repeat')} />}</Field>
                )}
                <div role="status" aria-live="polite" className="error-text" style={{ minHeight: 22 }}>{error}</div>
                <Button type="submit" disabled={busy} style={{ height: 44 }}>{firstRun ? 'Create account' : 'Sign in'}</Button>
              </form>
            </>
          )}
        </motion.div>
      </div>
    </div>
  )
}
