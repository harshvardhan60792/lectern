// Three-dimensional building blocks: tilt cards, flip cards, floating paper.
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'motion/react'
import { useRef } from 'react'

/**
 * A card that leans toward the pointer, like picking up a sheet of card.
 * Decorative only: it never moves content out of reach, and it stops with reduced motion.
 */
export function TiltCard({ children, max = 7, className = '', style, lift = true, ...rest }) {
  const reduce = useReducedMotion()
  const ref = useRef(null)
  const px = useMotionValue(0)
  const py = useMotionValue(0)
  const rx = useSpring(useTransform(py, [-0.5, 0.5], [max, -max]), { stiffness: 180, damping: 18 })
  const ry = useSpring(useTransform(px, [-0.5, 0.5], [-max, max]), { stiffness: 180, damping: 18 })
  const glareX = useTransform(px, [-0.5, 0.5], ['0%', '100%'])
  const glareY = useTransform(py, [-0.5, 0.5], ['0%', '100%'])
  const glare = useTransform([glareX, glareY], ([x, y]) => `radial-gradient(360px circle at ${x} ${y}, rgba(255,255,255,.22), transparent 55%)`)

  const onMove = (e) => {
    if (reduce || e.pointerType !== 'mouse') return
    const r = ref.current.getBoundingClientRect()
    px.set((e.clientX - r.left) / r.width - 0.5)
    py.set((e.clientY - r.top) / r.height - 0.5)
  }
  const onLeave = () => { px.set(0); py.set(0) }

  return (
    <motion.div
      ref={ref}
      className={`card tilt ${className}`}
      style={{ ...style, rotateX: reduce ? 0 : rx, rotateY: reduce ? 0 : ry, transformStyle: 'preserve-3d', transformPerspective: 900 }}
      whileHover={lift && !reduce ? { y: -4, boxShadow: 'var(--shadow-lift)' } : undefined}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      {...rest}
    >
      {children}
      {!reduce && <motion.span aria-hidden className="glare" style={{ background: glare }} />}
    </motion.div>
  )
}

/** A card with two faces. `flipped` turns it over; reduced motion cross-fades instead. */
export function FlipCard({ flipped, front, back, height, className = '' }) {
  const reduce = useReducedMotion()
  if (reduce) {
    return <div className={className} style={{ minHeight: height }}>{flipped ? back : front}</div>
  }
  return (
    <div className={`flip ${className}`} style={{ perspective: 1400, minHeight: height }}>
      <motion.div className="flip-inner" animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ type: 'spring', stiffness: 140, damping: 18 }} style={{ transformStyle: 'preserve-3d', minHeight: height }}>
        <div className="flip-face" aria-hidden={flipped}>{front}</div>
        <div className="flip-face flip-back" aria-hidden={!flipped}>{back}</div>
      </motion.div>
    </div>
  )
}

/** Paper that drifts a few pixels, as if lying on a breathing desk. */
export function Float({ children, delay = 0, distance = 8, duration = 6, rotate = 1.2, style, className }) {
  const reduce = useReducedMotion()
  if (reduce) return <div style={style} className={className}>{children}</div>
  return (
    <motion.div className={className} style={style}
      animate={{ y: [0, -distance, 0], rotate: [0, rotate, 0] }}
      transition={{ duration, delay, repeat: Infinity, ease: 'easeInOut' }}>
      {children}
    </motion.div>
  )
}
