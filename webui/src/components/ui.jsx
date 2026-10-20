import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Search, X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { ease, spring, springSoft } from '../lib/format'

export function Button({ kind = 'primary', size, icon: Icon, children, className = '', ...rest }) {
  return (
    <button className={`btn btn-${kind} ${size === 'sm' ? 'btn-sm' : ''} ${className}`} {...rest}>
      {Icon && <Icon size={size === 'sm' ? 15 : 17} strokeWidth={2} aria-hidden />}
      {children}
    </button>
  )
}

export function Pill({ tone, children, dot }) {
  return (
    <span className={`pill ${tone || ''}`}>
      {dot && <span className="dot" aria-hidden />}
      {children}
    </span>
  )
}

export function Field({ label, children, hint }) {
  const id = useId()
  const child = typeof children === 'function' ? children(id) : children
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      {child}
      {hint && <span className="xsmall faint">{hint}</span>}
    </div>
  )
}

export function SearchInput({ value, onChange, placeholder = 'Search', width = 280, autoFocus }) {
  return (
    <div className="search-wrap" style={{ width }}>
      <Search size={16} aria-hidden />
      <input
        className="input input-search"
        value={value}
        placeholder={placeholder}
        aria-label={placeholder}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

export function Select({ value, onChange, options, label, width }) {
  return (
    <select className="select" style={{ width }} value={value ?? ''} aria-label={label}
      onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={String(o.value)} value={o.value ?? ''}>{o.label}</option>
      ))}
    </select>
  )
}

export function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  )
}

/** Segmented tabs; the paper marker slides between them. */
export function Tabs({ value, onChange, items, id = 'tabs' }) {
  return (
    <div className="tabs" role="tablist">
      {items.map((it) => {
        const key = typeof it === 'string' ? it : it.value
        const label = typeof it === 'string' ? it : it.label
        const selected = key === value
        return (
          <button key={key} role="tab" aria-selected={selected} className="tab" onClick={() => onChange(key)}>
            {selected && <motion.span layoutId={`${id}-marker`} className="tab-marker" transition={spring} />}
            <span>{label}</span>
          </button>
        )
      })}
    </div>
  )
}

export function Stat({ label, value, note, tone }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={tone ? { color: `var(--${tone})` } : undefined}>{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  )
}

/**
 * A data table. columns: [{ key, label, align: 'r', render(row) }].
 * Paging is shown when `total` and `onPage` are given.
 */
export function Table({ columns, rows, onRowClick, selectedKey, rowKey = 'id', total, offset = 0, pageSize, onPage, empty, maxHeight }) {
  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="table-wrap" style={{ maxHeight }}>
        <table className={`table ${onRowClick ? 'clickable' : ''}`}>
          <thead>
            <tr>{columns.map((c) => <th key={c.key} className={c.align === 'r' ? 'r' : ''} style={{ width: c.width }}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const key = row[rowKey] ?? i
              return (
                <tr key={key} aria-selected={selectedKey !== undefined && key === selectedKey}
                  tabIndex={onRowClick ? 0 : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter') onRowClick(row) } : undefined}>
                  {columns.map((c) => (
                    <td key={c.key} className={`${c.align === 'r' ? 'r' : ''} ${c.wrap ? 'wrap' : ''}`}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
        {rows.length === 0 && (empty || <Empty title="Nothing here yet" />)}
      </div>
      {onPage && total > 0 && (
        <div className="pager">
          <span className="num">{(offset + 1).toLocaleString()}–{(offset + rows.length).toLocaleString()} of {total.toLocaleString()}</span>
          <div className="row">
            <Button kind="secondary" size="sm" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - pageSize))}>Previous</Button>
            <Button kind="secondary" size="sm" disabled={offset + rows.length >= total} onClick={() => onPage(offset + pageSize)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}

function useEscape(onClose) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
}

/** A paper sheet that slides in from the right over the list. */
export function Sheet({ open, onClose, title, subtitle, actions, children, width }) {
  const reduce = useReducedMotion()
  return (
    <AnimatePresence>
      {open && (
        <SheetInner key="sheet" onClose={onClose} title={title} subtitle={subtitle} actions={actions} width={width} reduce={reduce}>
          {children}
        </SheetInner>
      )}
    </AnimatePresence>
  )
}

function SheetInner({ onClose, title, subtitle, actions, children, width, reduce }) {
  useEscape(onClose)
  const ref = useRef(null)
  useEffect(() => { ref.current?.focus() }, [])
  return (
    <>
      <motion.div className="scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }} />
      <motion.aside
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : 'Details'}
        className="sheet"
        style={width ? { width } : undefined}
        initial={reduce ? { opacity: 0 } : { transform: 'translateX(105%) rotateY(-8deg)', opacity: 0.6 }}
        animate={reduce ? { opacity: 1 } : { transform: 'translateX(0%) rotateY(0deg)', opacity: 1 }}
        exit={reduce ? { opacity: 0 } : { transform: 'translateX(105%) rotateY(-4deg)', opacity: 0.8, transition: { duration: 0.2, ease } }}
        transition={springSoft}
      >
        <div className="sheet-head">
          <div style={{ minWidth: 0 }}>
            {typeof title === 'string' ? <h2 className="card-title" style={{ fontSize: 'var(--fs-xl)' }}>{title}</h2> : title}
            {subtitle && <div className="card-sub">{subtitle}</div>}
          </div>
          <div className="row">
            {actions}
            <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={17} /></button>
          </div>
        </div>
        <div className="sheet-body">{children}</div>
      </motion.aside>
    </>
  )
}

/** A centred dialog for short forms and confirmations. */
export function Dialog({ open, onClose, title, children, footer, intro }) {
  return (
    <AnimatePresence>
      {open && <DialogInner key="dialog" onClose={onClose} title={title} footer={footer} intro={intro}>{children}</DialogInner>}
    </AnimatePresence>
  )
}

function DialogInner({ onClose, title, children, footer, intro }) {
  useEscape(onClose)
  return (
    <>
      <motion.div className="scrim dialog-scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.12 } }} />
      <motion.div className="dialog" role="dialog" aria-modal="true" aria-label={title}
        initial={{ opacity: 0, transform: 'translate(-50%, -48%) scale(.96) rotateX(6deg)' }}
        animate={{ opacity: 1, transform: 'translate(-50%, -50%) scale(1) rotateX(0deg)' }}
        exit={{ opacity: 0, transform: 'translate(-50%, -49%) scale(.98)', transition: { duration: 0.12 } }}
        transition={spring}>
        <h2 className="dialog-title">{title}</h2>
        {intro && <p className="muted small" style={{ marginBottom: 14 }}>{intro}</p>}
        <div className="stack" style={{ gap: 14, marginTop: 10 }}>{children}</div>
        {footer && <div className="row" style={{ justifyContent: 'flex-end', marginTop: 22 }}>{footer}</div>}
      </motion.div>
    </>
  )
}

/** Confirm a destructive action. */
export function Confirm({ open, onClose, title, text, action = 'Remove', onConfirm }) {
  return (
    <Dialog open={open} onClose={onClose} title={title}
      footer={<><Button kind="secondary" onClick={onClose}>Cancel</Button><Button kind="danger" onClick={() => { onClose(); onConfirm() }}>{action}</Button></>}>
      <p className="muted">{text}</p>
    </Dialog>
  )
}

export function PageHead({ title, sub, actions }) {
  return (
    <header className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        {sub && <p className="page-sub">{sub}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

export function Loading({ height = 160 }) {
  return <div className="skeleton" style={{ height }} aria-label="Loading" />
}
