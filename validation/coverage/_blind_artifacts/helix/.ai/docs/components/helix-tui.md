<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: helix-tui
 path: helix-tui
 inputs: helix-tui/src/**, helix-tui/Cargo.toml, root Cargo.toml
 doc_in_inputs: false
 date: 2026-06-13
 rule: R1 (no fabrication; every claim grounded to file:line)
-->

# Component: helix-tui

A workspace member crate (`helix-tui/Cargo.toml:2`); declared as a member of the root workspace at `Cargo.toml:7`.

## Role

- An immediate-mode terminal-UI rendering library — a double-buffered cell grid plus a swappable terminal `Backend` trait, a constraint-solver layout engine, and a set of drawable widgets — that emits only the minimal diff of changed cells to the terminal each frame. helix-tui/Cargo.toml:3
- The library crate root only re-exports the terminal frontend types and declares the module surface (`backend`, `buffer`, `layout`, `symbols`, `terminal`, `text`, `widgets`). helix-tui/src/lib.rs:1

## Dependencies (edges)

- **helix-view** (workspace path dep, with the `term` feature): the only non-helix-core sibling crate it depends on; supplies the rendering vocabulary (`graphics::{Rect, Style, Color, Modifier, UnderlineStyle, CursorKind, Margin}`, `editor::Config`/`KittyKeyboardProtocolConfig`, `theme::{Mode, Color}`). Declared at helix-tui/Cargo.toml:18; used in buffer/layout/terminal/backends, e.g. helix-tui/src/buffer.rs:4, helix-tui/src/layout.rs:10, helix-tui/src/terminal.rs:5, helix-tui/src/backend/mod.rs:7.
- **helix-core** (workspace path dep): used only for text-measurement / line-ending utilities — `unicode::width::{UnicodeWidthChar, UnicodeWidthStr}` and `line_ending::str_is_line_ending`. Declared at helix-tui/Cargo.toml:19; used at helix-tui/src/buffer.rs:3, helix-tui/src/text.rs:49, helix-tui/src/widgets/reflow.rs:2, helix-tui/src/widgets/table.rs:7.
- No code edge to helix-term, helix-lsp, helix-lsp-types, helix-event, helix-dap, helix-dap-types, helix-loader, helix-vcs, helix-parsec, helix-stdx, or xtask — a full grep of `helix-tui/src` for `helix_*` paths returns only `helix_view` and `helix_core` (every other match is a `helix_tui::` self-reference inside doctests). helix-tui/Cargo.toml:17

## Data

- Owns no database or file persistence. The only `Write` to an OS handle is the ANSI cursor-reset byte stream sent to the backend's writer in `restore`. helix-tui/src/backend/crossterm.rs:210
- Reads (does not write) process environment variables for terminal-capability detection: `TERM_PROGRAM`, `TERM`, `VTE_VERSION` (crossterm backend) and additionally `TMUX` (termina backend). helix-tui/src/backend/crossterm.rs:27, helix-tui/src/backend/termina.rs:41, helix-tui/src/backend/termina.rs:105
- Reads the terminfo capability database via `termini::TermInfo::from_env` to detect extended-underline support and the cursor-reset sequence. helix-tui/src/backend/crossterm.rs:77
- In-memory state stores: the `Terminal` holds two screen `Buffer`s (`buffers: [Buffer; 2]`) — current + previous. helix-tui/src/terminal.rs:67. A `Buffer` is a flat `Vec<Cell>` of length `area.width * area.height`. helix-tui/src/buffer.rs:167. Layout results are memoized in a thread-local `LAYOUT_CACHE: HashMap<(Rect, Layout), Vec<Rect>>`. helix-tui/src/layout.rs:70

## Boundary rules

- Backend abstraction boundary: all terminal I/O goes through the `Backend` trait, never directly; the concrete backend is selected by `cfg` — `TerminaBackend` on non-Windows, `CrosstermBackend` on Windows (both gated on the `termina` feature), plus a `TestBackend`. helix-tui/src/backend/mod.rs:12, helix-tui/src/backend/mod.rs:17, helix-tui/src/backend/mod.rs:22
- Widget-to-buffer boundary: "No widget in the library interacts directly with the terminal" — every widget renders into the intermediate `Buffer` only, never the terminal. helix-tui/src/buffer.rs:139. Enforced by the `Widget` trait whose sole method `render(self, area: Rect, buf: &mut Buffer)` takes a buffer, not a backend. helix-tui/src/widgets/mod.rs:46
- Default feature set is `["termina", "crossterm"]`; `crossterm` is a Windows-only dependency (`[target.'cfg(windows)'.dependencies]`), `termina` is optional. helix-tui/Cargo.toml:15, helix-tui/Cargo.toml:30
- Crate-private render fast-path: `Cell::set_symbol_with_width` and `Buffer::set_grapheme` are `pub(crate)` / hot-path-only entry points that skip the public path's segmentation + width recomputation. helix-tui/src/buffer.rs:45, helix-tui/src/buffer.rs:382
- Layout values flow one way: a `helix_view::editor::Config` is converted into the TUI's own `terminal::Config` via `From<&EditorConfig>` (TUI never mutates the editor config). helix-tui/src/terminal.rs:31

## Key facts

- Double-buffered diff rendering: `Terminal::flush` diffs the previous buffer against the current and sends only changed cells to the backend; after each `draw`, the back buffer is reset and the `current` index is flipped (`self.current = 1 - self.current`). helix-tui/src/terminal.rs:151, helix-tui/src/terminal.rs:208
- The diff algorithm is multi-width-aware: it assumes well-formed buffers (no double-width cell followed by a non-blank cell) and uses `to_skip`/`invalidated` counters so a wide grapheme correctly suppresses/forces redraw of the column it covers. helix-tui/src/buffer.rs:706, helix-tui/src/buffer.rs:730
- A `Cell` stores one styled grapheme in an inline `ArrayString<28>` (`SYMBOL_CAPACITY = 28`); a grapheme exceeding 28 bytes is replaced with U+FFFD (`�`) rather than allocating or panicking. helix-tui/src/buffer.rs:8, helix-tui/src/buffer.rs:25, helix-tui/src/buffer.rs:37
- Performance invariant: `Cell` caches its display `width: u8` so the hot render path avoids recomputing unicode width per cell. helix-tui/src/buffer.rs:15
- Layout uses the Cassowary linear-constraint solver (`cassowary` crate) with `REQUIRED` and `WEAK` strengths to split a `Rect` per a list of `Constraint`s (`Percentage`/`Ratio`/`Length`/`Max`/`Min`), then nudges the last element to absorb rounding error. helix-tui/src/layout.rs:6, helix-tui/src/layout.rs:30, helix-tui/src/layout.rs:304
- `Layout::split` results are memoized in a thread-local cache keyed by `(Rect, Layout)`, so repeated splits of the same area/layout are O(1). helix-tui/src/layout.rs:70, helix-tui/src/layout.rs:179
- Default terminal geometry is 80x24 (`DEFAULT_TERMINAL_SIZE`), used as the fallback whenever the backend cannot report a size. helix-tui/src/terminal.rs:77, helix-tui/src/terminal.rs:91
- Terminal capabilities are detected once and cached: `supports_keyboard_enhancement_protocol` is a `OnceCell<bool>` resolved on first use; extended-underline support is read from terminfo (`Smulx`/`Su`), VTE version >= 5102, or `TERM_PROGRAM == WezTerm`. helix-tui/src/backend/crossterm.rs:102, helix-tui/src/backend/crossterm.rs:86
- The crossterm backend deliberately emits colon-separated SGR underline-color sequences (`\x1b[58:...`) rather than the more common semicolon form, to avoid visual artifacts on terminals that lack colored-underline support. helix-tui/src/backend/crossterm.rs:407, helix-tui/src/backend/crossterm.rs:425
- The text model is a 3-level hierarchy: `Span` (one style) -> `Spans` (one line, per-grapheme styles) -> `Text` (multiple lines). helix-tui/src/text.rs:1
- The `Terminal::draw` legacy closure/`Frame` API is commented out; the live `draw(cursor_position, cursor_kind)` signature flushes, positions/shapes the cursor, then swaps buffers. helix-tui/src/terminal.rs:129, helix-tui/src/terminal.rs:179
- The `list` widget is currently disabled — `mod list;` and its re-exports are commented out in the widgets module; the shipped widgets are `Block`, `Paragraph`, and `Table`. helix-tui/src/widgets/mod.rs:13, helix-tui/src/widgets/mod.rs:18
<!-- DEEPINIT:END -->
