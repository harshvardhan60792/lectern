import { Command } from 'cmdk'
import {
  Award, BookOpen, ChartColumn, ClipboardList, Gauge, GraduationCap, Library, LogOut, MessageSquareText,
  Moon, Search, ShieldAlert, Sun, UserCog, Users,
} from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { initials, spring } from '../lib/format'

export const STAFF_NAV = [
  { key: 'overview', label: 'Overview', icon: Gauge },
  { key: 'students', label: 'Students', icon: Users },
  { key: 'courses', label: 'Courses', icon: Library },
  { key: 'enrollments', label: 'Enrollments', icon: ClipboardList },
  { key: 'questions', label: 'Question bank', icon: BookOpen },
  { key: 'reports', label: 'Reports', icon: ChartColumn },
  { key: 'ask', label: 'Ask the data', icon: MessageSquareText },
  { key: 'risk', label: 'At-risk students', icon: ShieldAlert },
  { key: 'certificates', label: 'Certificates', icon: Award },
]
const ADMIN_NAV = [{ key: 'accounts', label: 'Accounts', icon: UserCog }]
export const STUDENT_NAV = [
  { key: 'learn', label: 'My learning', icon: GraduationCap },
  { key: 'catalog', label: 'Browse courses', icon: Library },
  { key: 'certificates', label: 'Certificates', icon: Award },
]

export function navFor(session) {
  if (session.role === 'student') return STUDENT_NAV
  return session.role === 'admin' ? [...STAFF_NAV, ...ADMIN_NAV] : STAFF_NAV
}

const ROLE = { admin: 'Administrator', instructor: 'Instructor', student: 'Student' }

export function Sidebar({ session, current, onGo, onSignOut, theme, onTheme, onPalette }) {
  const items = navFor(session)
  return (
    <aside className="side">
      <div className="brand">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
          <path d="M5 10.5c3.6-1.5 7.4-1.5 11 .6 3.6-2.1 7.4-2.1 11-.6v13c-3.6-1.5-7.4-1.5-11 .6-3.6-2.1-7.4-2.1-11-.6z" fill="#E8ECE2" />
          <path d="M16 11.1v13.5" stroke="#D4A445" strokeWidth="1.6" />
        </svg>
        <span className="brand-word">Lectern</span>
      </div>
      <div className="brand-role">{ROLE[session.role]}</div>
      <nav className="nav" aria-label="Main">
        {items.map(({ key, label, icon: Icon }) => {
          const active = current === key
          return (
            <button key={key} className="nav-item" aria-current={active ? 'page' : undefined} onClick={() => onGo(key)}>
              {active && <motion.span layoutId="nav-active" className="nav-active" transition={spring} />}
              <Icon size={18} strokeWidth={active ? 2.3 : 1.9} aria-hidden />
              <span>{label}</span>
            </button>
          )
        })}
      </nav>
      <div className="side-foot">
        <button className="side-btn" onClick={onPalette} style={{ justifyContent: 'space-between' }}>
          <span className="row" style={{ gap: 6 }}><Search size={14} aria-hidden />Go to…</span>
          <span className="kbd">Ctrl K</span>
        </button>
        <div className="side-user">
          <span className="avatar" aria-hidden>{initials(session.display_name)}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--fs-sm)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{session.display_name}</div>
            <div className="xsmall" style={{ color: 'var(--on-slate-2)' }}>@{session.username}</div>
          </div>
        </div>
        <div className="side-actions">
          <button className="side-btn" onClick={onTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} appearance`}>
            {theme === 'dark' ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}{theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <button className="side-btn" onClick={onSignOut}><LogOut size={14} aria-hidden />Sign out</button>
        </div>
      </div>
    </aside>
  )
}

/** Ctrl+K: jump anywhere. Opens instantly (no animation) because it's used constantly. */
export function CommandPalette({ open, onClose, session, onGo, extra = [] }) {
  const [value, setValue] = useState('')
  useEffect(() => { if (open) setValue('') }, [open])
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <>
      <div className="scrim" style={{ zIndex: 59, backdropFilter: 'none' }} onClick={onClose} />
      <Command className="palette" label="Go to" style={{ transform: 'translateX(-50%)' }}>
        <Command.Input autoFocus value={value} onValueChange={setValue} placeholder="Go to a screen or action…" />
        <Command.List>
          <Command.Empty>Nothing matches. Try a screen name, like “Reports”.</Command.Empty>
          <Command.Group heading="Screens">
            {navFor(session).map(({ key, label, icon: Icon }) => (
              <Command.Item key={key} value={label} onSelect={() => { onGo(key); onClose() }}>
                <Icon size={16} aria-hidden />{label}
              </Command.Item>
            ))}
          </Command.Group>
          {extra.length > 0 && (
            <Command.Group heading="Actions">
              {extra.map((a) => (
                <Command.Item key={a.label} value={a.label} onSelect={() => { a.run(); onClose() }}>
                  <a.icon size={16} aria-hidden />{a.label}
                </Command.Item>
              ))}
            </Command.Group>
          )}
        </Command.List>
      </Command>
    </>
  )
}
