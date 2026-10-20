import { Moon, Plus, Sun } from 'lucide-react'
import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { StrictMode, useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'sonner'
import './styles/tokens.css'
import './styles/components.css'
import './styles/depth.css'
import { CommandPalette, Sidebar, navFor } from './components/Shell'
import { Loading } from './components/ui'
import { api } from './lib/api'
import { pageVariants } from './lib/format'
import Accounts from './screens/Accounts'
import Ask from './screens/Ask'
import Catalog from './screens/Catalog'
import Certificates from './screens/Certificates'
import Courses from './screens/Courses'
import Enrollments from './screens/Enrollments'
import Learn from './screens/Learn'
import Overview from './screens/Overview'
import Questions from './screens/Questions'
import Reports from './screens/Reports'
import Risk from './screens/Risk'
import SignIn from './screens/SignIn'
import Students from './screens/Students'

const SCREENS = {
  overview: Overview, students: Students, courses: Courses, enrollments: Enrollments, questions: Questions,
  reports: Reports, ask: Ask, risk: Risk, certificates: Certificates, accounts: Accounts, learn: Learn, catalog: Catalog,
}

function initialTheme() {
  try {
    return localStorage.getItem('lectern-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  } catch {
    return 'light'
  }
}

function App() {
  const [state, setState] = useState(null)
  const [route, setRoute] = useState({ name: null, params: {}, dir: 1 })
  const [palette, setPalette] = useState(false)
  const [theme, setTheme] = useState(initialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('lectern-theme', theme) } catch { /* private mode: fine */ }
  }, [theme])

  useEffect(() => {
    api('state').then(setState).catch((e) => setState({ db_ready: true, has_users: true, session: null, error: e.message }))
  }, [])

  const session = state?.session
  const nav = useMemo(() => (session ? navFor(session) : []), [session])

  const go = useCallback((name, params = {}) => {
    setRoute((r) => {
      const from = nav.findIndex((n) => n.key === r.name)
      const to = nav.findIndex((n) => n.key === name)
      return { name, params, dir: to >= from ? 1 : -1, stamp: Date.now() }
    })
  }, [nav])

  useEffect(() => {
    if (session && !route.name) setRoute({ name: nav[0].key, params: {}, dir: 1 })
  }, [session, route.name, nav])

  // Lets automated screen checks switch screens (scripts/check_screens.py).
  useEffect(() => { window.lecternGo = go }, [go])

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && session) {
        e.preventDefault()
        setPalette((p) => !p)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [session])

  if (!state) return <div style={{ padding: 40 }}><Loading height={300} /></div>

  if (!session) {
    return (
      <MotionConfig reducedMotion="user">
        <SignIn state={state} onSignedIn={(s) => setState((st) => ({ ...st, session: s, has_users: true }))} />
        <Toaster position="bottom-right" />
      </MotionConfig>
    )
  }

  const signOut = async () => {
    await api('logout')
    setRoute({ name: null, params: {}, dir: 1 })
    setState((st) => ({ ...st, session: null }))
  }
  const Screen = SCREENS[route.name]

  return (
    <MotionConfig reducedMotion="user">
      <div className="shell">
        <Sidebar session={session} current={route.name} onGo={go} onSignOut={signOut}
          theme={theme} onTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))} onPalette={() => setPalette(true)} />
        <main className="main">
          <AnimatePresence mode="popLayout" initial={false} custom={route.dir}>
            <motion.div key={`${route.name}-${route.stamp || 0}`} className="page" custom={route.dir}
              variants={pageVariants} initial="initial" animate="enter" exit="exit">
              {Screen && <Screen session={session} params={route.params} go={go} />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} session={session} onGo={go}
        extra={[
          ...(session.role !== 'student' ? [
            { label: 'Add a student', icon: Plus, run: () => go('students', { add: true }) },
            { label: 'New course', icon: Plus, run: () => go('courses', { add: true }) },
          ] : []),
          { label: theme === 'dark' ? 'Light appearance' : 'Dark appearance', icon: theme === 'dark' ? Sun : Moon, run: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) },
        ]} />
      <Toaster position="bottom-right" toastOptions={{ className: 'lectern-toast' }} />
    </MotionConfig>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
