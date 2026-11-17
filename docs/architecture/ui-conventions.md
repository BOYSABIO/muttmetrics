# UI conventions: where buttons go, how things move, and what makes a sound

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

## Motion

Added in 0.8.0. Motion is there to explain what just happened, so the app feels
like one thing instead of a stack of pages. It is decoration on top of a screen
that already works: remove `motion.css` from `main.tsx` and nothing breaks.

| Rule | What it means here |
|---|---|
| **Motion says where you went** | Deeper (a client, the next wizard step) slides in from the right; back slides the other way; New visit rises from the bottom and drops away when closed. One helper, `withTransition(update, kind)`, with `forward` / `back` / `up` / `down` / `fade` |
| **Things that stay, stay** | The header, the wizard's step tracker and its bottom bar don't move during a screen change; only the content between them does. The nav pill slides between *Home* and *Clients*; a pet's avatar travels from its row to its profile |
| **Never wait for an animation** | Nothing is longer than about a second, the long ones (bars growing, numbers counting) never block a tap, and no button is disabled while something animates |
| **A message never moves the page** | Status lines are a toast floating above the bottom bar (`Toast`). Good news leaves by itself; a problem stays until the next action or its ✕. A screen has at most one `role="status"` line |
| **Loading has a shape** | A skeleton of what is coming (`DashboardSkeleton`, `ListSkeleton`), not the word "Loading" |
| **A working button says so in place** | `.btn-busy` puts a spinner inside the button at the same width; the label doesn't change to "Saving…" |
| **Numbers count, bars grow** | The dashboard's headline numbers count to their value (`useCountUp`), from the last value when you change week. Bars and the milestone line draw themselves once |
| **One celebration** | Saving a visit is the only moment that gets a show: the stamp, a short burst of confetti, the visit read back like a receipt, and the week's take-home going up by what the groom earned. Everything else stays quiet |
| **Reduced motion is respected everywhere** | With the device's *Reduce motion* setting on, screens cut instead of slide, numbers show their value at once, nothing loops, and the phone doesn't buzz. The guard is at the end of `motion.css`; `reducedMotion()` in `motion.ts` is the same check for code. The e2e tests run this way |

**Timings and curves** are tokens in `motion.css` (`--dur-1` … `--dur-4`, `--ease-out`, `--ease-spring`): a press is about 120 ms, a chip or toast 220 ms, a screen change or a card arriving 380 ms, a bar or a number 650 ms. Use the tokens; don't invent a new duration per component.

**No animation library.** Screen changes use the browser's View Transitions (`document.startViewTransition`); where a browser doesn't have them the change just happens. Everything else is CSS keyframes and one `requestAnimationFrame` loop for numbers.

**The timer** is a stopwatch face (`TimerDial`): sixty ticks light up through each minute and a hand goes round once a minute, so a glance from across the room says "it's running". The hand's position is information, so it still moves under reduced motion (in steps); the ripple around the dial does not.

## Sound

Added in 0.8.0 (`frontend/src/sound.ts`). Five short tones made in the browser, no audio files:

| Sound | When |
|---|---|
| `start` / `stop` | The timer starts (two notes up) / stops (the same two, down) |
| `saved` | A visit is saved: a soft stamp, then three notes as the take-home counts up |
| `done` | A success toast (a profile saved, a pet added) |
| `problem` | A toast that needs attention: one low note, not a buzzer |

- **A sound confirms, it never informs.** Everything a sound says is also on the screen; with sound off nothing is lost.
- **Quiet and short.** One master volume (`MASTER`), under 0.4 s each except the last note of `saved`. Taps, chips and screen changes make no sound: a sound on everything is noise.
- **One switch.** *Sound on / off* sits next to the version; the choice is stored on the device. On an iPhone the silent switch mutes it too; on Android it follows the media volume (both the browser's doing).
- Browsers only allow sound after a tap, so the first tap starts the audio engine; a sound never plays before one.
- New sound? Add it to `SOUNDS` and to the table above, and ask whether the moment really needs one.

## The dogs

Added in 0.8.0 (`frontend/src/PixelDogs.tsx`, `pixelSprites.ts`, `dogs.css`). Two pixel-art dogs, drawn as squares in code (a letter per square, 16 × 18, seen from the front), so there are no image files.

| Dog | Character | Where |
|---|---|---|
| **Collie** (black and white, tongue out) | The happy one | Corner of an empty week; on the Saved screen's milestone line (hops when the money lands); the waiting scene |
| **Guard** (all black, tan eyebrow dots, never changes his face) | Guards whatever matters | Looks over the top of the take-home card, tail wagging beside his head; next to the collie on the Saved screen (tail wagging); in the *Delete this visit* box; the waiting scene |

- **They mean something where they sit.** The guard is only ever next to something worth guarding (money, a delete). Don't scatter them as decoration.
- **The waiting scene** (`DogsWaiting`): both dogs look over a line at you. The collie pants, his tongue hanging over the line; the guard looks at him now and then and blinks; both tails wag. It appears only when a wait gets long (`useSlow`: about a second on a loading page, 0.7 s on a tap), so a fast load never flashes it.
- **His face never moves; his tail does.** The guard's tail wags only where there is something to be pleased about (`wag`, and always when he looks over an edge). In the delete box it is still. The collie's never stops.
- **A wag is two drawings of the same tail, up and down, swapped.** Don't animate a tail by changing its shape in place: that reads as swelling, not wagging.
- **No outline around a dog.** No light edge on dark cards. The one exception is a thin dark edge on the collie, whose white fur would vanish on a cream card.
- Pixel art stays on its grid: move a dog by whole squares (its `scale` in px) and never rotate or stretch it.
- Always `aria-hidden`; frames are swapped with `steps()` animations, which the reduced-motion guard stops.

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
- `frontend/src/motion.ts`: `withTransition`, `useCountUp`, `haptic`, `reducedMotion`.
- `frontend/src/motion.css`: timing tokens, entrance and chart animations, the
  screen-change rules (`html[data-vt=…]`), the reduced-motion guard. Loaded last.
- `frontend/src/ui.tsx` + `ui.css`: `Toast`, the skeletons, the icons, and the
  styles for the timer dial, the saved screen and avatars without a photo.
- `frontend/src/TimerDial.tsx`, `frontend/src/SaveCelebration.tsx`: the two
  set pieces of New visit.
- `frontend/src/sound.ts`: `play(name)`, the sounds, the on / off setting.
- `frontend/src/PixelDogs.tsx` + `dogs.css`: `PixelDog`, `DogsWaiting`, where
  the dogs sit; `SlowOverlay` (ui.tsx) and `useSlow` (motion.ts) decide when a
  wait is long enough to show them.
