// Shared motion language (see DESIGN.md › Motion).
export const spring = { type: 'spring', stiffness: 380, damping: 32, mass: 0.9 }
export const springSoft = { type: 'spring', stiffness: 220, damping: 26 }
export const ease = [0.2, 0.8, 0.2, 1]
export const appear = { duration: 0.26, ease }

// Screens slide in from the side they were picked from; never fade-up on load.
export const pageVariants = {
  initial: (dir) => ({ opacity: 0, x: dir * 28 }),
  enter: { opacity: 1, x: 0, transition: { ...springSoft, opacity: { duration: 0.2 } } },
  exit: (dir) => ({ opacity: 0, x: dir * -18, transition: { duration: 0.14, ease } }),
}
