# UI conventions: where buttons go

The groomer uses the app fast, often one-handed, between dogs. Muscle memory is
the point: if *Back* is top left on one screen, it is top left on all of them,
and nothing dangerous ever sits where a common button sits on another screen.

Every new screen follows these rules. If a screen needs to break one, write
down why here first.

## The rules

| What | Where | Label |
|---|---|---|
| **Leave this screen** | Top left, first thing on the page (`PageBack`) | `← Back` on pages; `✕ Close` in the New visit flow |
| **Main action** (save, continue) | Bottom bar (`.action-bar`), **rightmost** | `Save changes` on edit pages; `Continue` / `Save visit` in New visit |
| **Step back inside a flow** | Bottom bar, **left of** the main action | `← Back` |
| **Destructive** (delete) | Its own `.danger-zone` box at the **end of the page**, button on the **left**; always asks to confirm | `Delete <thing>` |
| **Start something new** (start visit) | Next to what it's for (the profile header), not in the bottom bar | `Start visit` |
| **Small inline pair** (e.g. Add pet) | Right-aligned in its card: `Cancel` then the action | `Cancel` / `<Action>` |
| **Main areas** | Header tabs, top right: `Home`, `Clients` (+ `New visit` on a computer; the round `+` on a phone) | — |

**Wizards (New visit):** the bottom bar is pinned to the bottom of the screen
(or of the card on a computer) on every step, even when the step is short, so
*Continue* never moves. On the first step, where there's no *Back*, its slot is
kept empty. Progress is a step tracker at the top, not "Step N of M".

**Fixed lists are taps, not dropdowns** (`ChoiceChips`): one tap with a dog on the table, every option visible, tap again to clear. **Yes / No** (`YesNo`) is two chips where neither means "nobody checked"; never a single checkbox for something a model may read. **Unsaved edits:** the bar says *Unsaved changes*, and Back asks before discarding them.

## Why these

- **Back top left, never in the bottom bar.** The bottom bar is where saving
  happens. Keeping "get me out" somewhere else means a quick exit can't save or
  delete by accident.
- **Primary rightmost.** On a phone the right thumb lands there; on a computer
  it's where the eye ends a form. It's the same spot on every screen, so the
  bar never reorders.
- **Delete never in the bar, and never on the right.** On a computer the bar is
  right-aligned; a delete button above it on the right would line up with Save.
  So the danger box sits at the end of the page with its button on the left,
  and there's a gap before the bar.
- **One label per meaning.** "Save changes" everywhere you edit, not "Save" here
  and "Update" there.

## In the code

- `frontend/src/PageBack.tsx`: the top-left button (`label="Close"` for capture).
- `.action-bar` (App.css): sticky bottom bar. Order in JSX = order on screen:
  secondary first, primary (`className="primary"`) last.
- `.danger-zone` / `.danger-zone-title` (App.css): end-of-page delete box.
- `.actions.inline-actions` (App.css): small right-aligned Cancel / Action pair.
- `.wizard-steps`, `.wizard-body`, `.wizard-bar`, `.slot-placeholder` (App.css):
  the pinned wizard bar and step tracker.
