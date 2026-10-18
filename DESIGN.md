# Lectern design

## Direction

Lectern is a classroom and a reading room: chalkboard slate, a brass desk lamp, index cards in a card-catalog drawer, and a book open on a stand. The interface is built from those materials. Courses are index cards that slide out of a drawer, mastery is a small skyline of blocks, the sign-in screen is a book opening on a lectern. Data screens stay calm and legible; the three-dimensional, moving pieces live in a few places where they explain something (a drawer you pull from, a card you flip to check, a block that rises as you learn).

Not the cream-paper, serif, clay-accent look, and no blue or purple anywhere.

## Colour

| Token | Light (day) | Dark (chalkboard) | Role |
|---|---|---|---|
| `--slate` | `#1E2B24` | `#111A15` | Sidebar, dark panels |
| `--bg` | `#E3E7DC` | `#16201B` | App background (sage paper / board) |
| `--card` | `#F6F7F2` | `#1F2C25` | Index cards, panels |
| `--card-2` | `#EDF0E7` | `#26352D` | Inset areas, table stripes |
| `--line` | `#C9D0C2` | `#34463B` | Borders, rules |
| `--ink` | `#18201B` | `#E8ECE2` | Main text (chalk in dark) |
| `--ink-2` | `#4E5A52` | `#A9B4AA` | Secondary text |
| `--brass` | `#B8862B` | `#D4A445` | Primary action fill (ink text on it) |
| `--brass-ink` | `#7A5714` | `#E2BC6A` | Brass as text/links |
| `--green` | `#2E6B47` | `#7DBB91` | Good, passed |
| `--amber` | `#94600E` | `#E0A94E` | Warning |
| `--red` | `#AE3A2A` | `#EE8A78` | Errors, withdrawn (teacher's red pen) |

Contrast: ink on card 15.6:1; ink-2 on card 6.6:1; ink on brass 6.1:1; brass-ink on card 5.9:1. Colour never carries meaning alone: every status also has a word.

## Type

- **Literata** (a typeface made for long reading on screens): page titles, numbers that matter, lesson text, certificate.
- **Atkinson Hyperlegible** (designed for legibility by the Braille Institute): everything else: navigation, controls, tables, labels.
- Scale (px): 13 · 15 · 17 (body) · 22 · 30 · 44 · 64. Tables 15, tabular figures. Lesson text 19/1.7 in Literata, max 68ch.
- Sentence case everywhere. No all-caps labels.

## Space, shape, depth

- Spacing steps: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64.
- Radius by role: controls 8, index cards 6 (paper is barely rounded), sheets 14, pills full.
- Depth is physical: paper cards sit on the desk with a short, warm-tinted shadow `0 1px 0 rgba(30,43,36,.08), 0 8px 24px -12px rgba(30,43,36,.35)`. Lifted things cast longer shadows. Blur (`backdrop-filter`) only on floating layers: command palette, side sheets, toasts.

## Motion

- Springs for things you move: `stiffness 380, damping 32` (snappy) and `220/26` (drawers, sheets).
- Ease for things that appear: `cubic-bezier(.2,.8,.2,1)`, 180–320 ms.
- One orchestrated moment: the sign-in book opening. Other motion answers an action (hover a card, open a drawer, flip a card, answer a question).
- 3D: `perspective 1200px`; tilt at most 8°; nothing spins for decoration.
- `prefers-reduced-motion`: springs become instant, tilt and float switch off, flips become cross-fades.

## Signature pieces

1. **Book on a lectern** (sign-in): pages turn once on load.
2. **Card-catalog drawer** (course catalog): index cards stacked in 3D; hovering lifts one out, clicking slides it fully out.
3. **Mastery skyline**: isometric blocks, height = mastery, colour + label = state.
4. **Flip cards**: quiz feedback and certificates turn over to show the answer / the fingerprint.
5. **Sliding sheets**: student and course details slide in from the right over the list.

## Anti-patterns for this project

Cream + serif + clay accent; blue or purple; gradient washes; identical rounded cards with the same grey shadow everywhere; all-caps eyebrows; emoji icons; "→" on buttons; fade-up on every section.
