# beforeshare design system

Read this before changing the site's UI. Do not introduce a new direction; extend this one. English only. Values below come from `docs/index.html` as of this commit.

## Concept

A scanner: a file is swept and each hidden thing it finds is tagged HIGH or MEDIUM.

Theme: dark (deliberate exception to the light-pages rule, pending the user's decision).

## Color tokens

| Token | Value | Role |
|---|---|---|
| `--bg` | `#07110d` | page background |
| `--fg` | `#d7f5e3` | body text |
| `--mut` | `#7fa592` | secondary text (AA on bg) |
| `--card` | `#0d1c15` | card and panel surface |
| `--line` | `#1d3a2c` | borders and dividers |
| `--acc` | `#2ee59d` | primary action, links, focus ring |
| `--accfg` | `#04150d` | text on accent |
| `--code` | `#030a07` | code block background |
| `--codefg` | `#b8f7d4` | code block text |
| `--warn` | `#e5b02e` | warning border and limits |

Contrast: every text node on the page is checked against WCAG AA (4.5:1, 3:1 for large text) with a script in the repo owner's QA harness. Keep it passing when you change a color.

## Type

| Token | Stack | Role |
|---|---|---|
| `--arabic` | `'IBM Plex Sans Arabic',sans-serif` | Arabic font stack |
| `--body` | `'Space Grotesk','IBM Plex Sans Arabic',system-ui,sans-serif` | body font stack |
| `--head` | `'JetBrains Mono','IBM Plex Sans Arabic',system-ui,sans-serif` | heading font stack |

Font sizes in use: `.86rem`, `1.5rem`, `1rem`, `.9rem`, `.72rem`, `clamp(2rem,8vw,2.8rem)`, `1.1rem`, `clamp(2rem,6.2vw,3.3rem)`, `1.15rem`, `.66rem`.

## Spacing, radius, elevation

- Spacing values in use: `2px`, `4px`, `6px`, `7px`, `8px`, `10px`, `11px`, `12px`, `14px`, `16px`, `26px`, `30px`. Prefer these; do not add new ones.
- Radius: `--r` (4px). Use the token, not literals.
- Elevation: `0 0 0 1px #000,0 0 40px rgba(46,229,157,.12)`, `0 0 18px 4px rgba(46,229,157,.55)`

## Motion

- Durations in use: `.05s`, `.15s`, `.25s`, `.2s`, `.34s`, `.42s`, `.4s`, `.5s`, `1.1s`, `1.9s`, `2.7s`, `3.4s`, `3.6s`.
- Curves: `cubic-bezier(.16,1,.3,1)`, `cubic-bezier(.22,1.36,.32,1)`.
- Every animation sits behind `prefers-reduced-motion: reduce`, which turns animation and transition off.
- Motion shows state or order. It is never decoration.

## Components and states

- Button `.btn` (filled) and `.btn.alt` (outline): min height 44px, visible `:focus-visible` outline (2px accent), hover and active states.
- Card `.card`, warning card `.card.warn` (left border in `--warn`).
- Language toggle `.langtoggle` with `aria-pressed`.
- Code block `pre`: always LTR, monospace.
- Status words use `.ok b` and `.no b` colors (AA checked).

## RTL rules

- The language toggle sets `dir` and `lang` on `<html>`. Arabic text uses the `--arabic` font and line-height 1.75.
- Use logical CSS (`margin-inline`, `inset-inline-start`, `text-align:start`). No `left` or `right` for layout.
- Letter-spacing is 0 and text-transform none in Arabic.
- Code, terminal output and demo panels stay LTR (`direction:ltr`). Install and demo output stay English.
- Arabic is Egyptian-leaning plain language. Brand names and commands stay Latin.

## Microcopy voice

Plain, specific, honest about limits. Say what it does and what it does not. No hype, no invented numbers.

Examples from the site:

1. Your files may reveal more than you think.
2. 3 hidden rows
3. A safe copy is not a guarantee.
4. Your original is never changed.
5. Pre-share file check

## Do / Don't

| Do | Don't |
|---|---|
| Name the exact finding | Say "issues found" |
| Rescan the copy and say so | Claim the copy is safe |
| Mono caps for scan labels | Mono for body text |
| Amber for HIGH, green for ok | Red for everything |
| Square 4px corners | Soft rounded cards |

## Known hard-coded values (should become tokens)

These literal colors appear in the CSS outside `:root`: `#000`, `#050d09`, `#0a1711`, `#0a1a13`, `#14281f`, `#2e9e5b`, `#4fd18b`, `#a9cdbb`, `#c0392b`, `#ff8f7e`.
Also: status colors in `.ok b` and `.no b`, and several literal pixel sizes in component CSS. Move them into tokens next time that block is touched.
