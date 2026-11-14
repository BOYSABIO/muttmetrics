# Pet data: what we record about an animal, and why

The pet profile is the input the later duration model (M7, [#121](https://github.com/BOYSABIO/muttmetrics/issues/121)) is meant to run on: **coat, size and handling**, without needing the breed ([`vision.md`](../product/vision.md), [`prior.md`](../prior.md)). So these fields have to be clean enough to train on, not just to read. This page is the contract. The allowed values live in one place, [`src/muttmetrics/pet_vocab.py`](../../src/muttmetrics/pet_vocab.py), and Postgres CHECKs enforce them. The words on screen live in [`frontend/src/petVocab.ts`](../../frontend/src/petVocab.ts).

## The rules

1. **Anything a model may read is a fixed list, enforced by the database.** Words on screen, codes underneath. No free text, and one spelling per meaning (`curly`, never `Curly`).
2. **Ordered things are numbers with one meaning:** handling 1–5, coat thickness 1–3, visit condition 0–5. The distance between values means something.
3. **Blank means "nobody checked", never "no".** Yes/no fields are nullable, and the app only sends the fields you changed, so saving a name can't write "no" into every unticked box. There's no `unknown` value for anything: unknown is NULL.
4. **Record where a value came from** when there are two ways to get it: `size_source` (`weight` / `eye`), `breed.source` (`catalog` / `salon`).
5. **Keep history.** Every profile save that changes a tracked field writes a `pet_change` row. Profiles are often filled in after the visits, and some facts change, so an analysis should use what was known on the visit date. For static facts (coat type), the latest value is usually the best one.
6. **One fact, one field.** Fields that restate another one were retired.
7. **Notes are for people.** Usual cut, temperament notes and health notes are free text and never model input. They aren't in the change log, and erase wipes them.

## The fields

| Field | Values | Why it's here |
|---|---|---|
| `species` | `dog`, `cat` | Everything else depends on it ([ADR-004](./adr/004-species.md)) |
| `breed_id` | catalog or salon breed | Cold-start prior (typical minutes, matting risk, rebook interval). Not required by the model |
| `breed_secondary_id` | a breed | "Crossed with", for mixes. Common crosses (doodles) are breeds of their own |
| `size_band` + `size_source` | `s`/`m`/`l`/`xl` + `weight`/`eye` | Size moves both time and price. From the weight when the pet was weighed; otherwise picked by eye. A weight always wins |
| `weight_kg` | > 0, ≤ 150 | The precise version of size, when someone weighs the dog |
| `coat_type` | dog: `smooth`, `double`, `curly`, `wire`, `silky`, `combination`; cat: `short`, `long` | The main time driver after size. One answer implies hair vs fur, undercoat and shedding |
| `coat_thickness` | 1 thin, 2 normal, 3 thick | How much coat to wash, dry and de-shed, which the type and breed can't tell you |
| `handling_score` | 1 easy, 2 calm, 3 some fuss, 4 difficult, 5 very difficult | Time and safety. Used by the rules prior |
| `muzzle_required`, `two_person_job` | true / false / NULL | Safety and staffing; two-person jobs cost two people's time |
| `senior_flag` | true / false / NULL | Older animals are slower and need breaks |
| `sex` | `female`, `male`, NULL | Kept; low value for grooming time |
| `usual_cut` | text | What the groomer needs at the next visit |
| `temperament_notes`, `health_notes` | text | For people |

**Coat types, for whoever picks them** (the groomer's own classification; check the words with him):

| Code | Label | Examples | Implies |
|---|---|---|---|
| `smooth` | Smooth | Boxer, French Bulldog | short, sheds |
| `double` | Double | Husky, Golden, Lab, German Shepherd | undercoat, sheds, de-shedding |
| `curly` | Curly | Poodle, Bichon, doodles | keeps growing, barely sheds, mats |
| `wire` | Wire | most terriers, Schnauzer | harsh coat, hand stripping |
| `silky` | Long & silky | Yorkie, Maltese, Shih Tzu | keeps growing, barely sheds, mats |
| `combination` | Combination | Cocker Spaniel, Setter | short body, long feathering |

### Retired (2026-11)

Not in the API or the UI. The columns stay until the real values have been checked, then a later migration drops them.

| Column | Why |
|---|---|
| `hair_or_fur`, `undercoat`, `sheds` | Implied by `coat_type` ("hair" coats = curly / silky / wire) |
| `coat_density` | Became `coat_thickness` (light → 1, medium → 2, dense → 3) |
| `mobility_notes`, `vet_notes` | Merged into `health_notes` |
| `fear_triggers[]`, `skin_conditions[]` | Never in the UI; the notes cover them |

## Breeds

- On screen: the English name. `name_de` is kept for search (accents optional) and for the seed.
- The catalog (`src/muttmetrics/seed/data.py`, about 77 breeds) carries the cold-start priors: typical minutes, matting risk, rebook interval, default coat and size. Starting guesses; correct them with the groomer.
- **Added in the salon** (`POST /breeds`, `breed.source = 'salon'`): only offered when nothing in the list matches what was typed. English names are unique per species, any capitalisation, and typing an existing German name returns that breed. A salon breed has no typical minutes, so the rules estimate stays empty for its dogs until someone fills them in (SQL or a seed entry; seeding a breed with the same name turns it into a catalog breed).
- Mixes: "Crossed with" (`breed_secondary_id`). Crosses groomed as their own thing (doodles) are breeds.
- On the server, update the catalog with `python -m muttmetrics.seed --breeds-only`. The full seed also rewrites services and would blank their prices without `data/private/pricing.json`.

## On screen

The profile asks the four **Basics** first (breed, size, coat, handling) as taps, with a filled count, because they're the model's main inputs. Yes / No fields are two chips where neither selected means "nobody checked"; tapping a selected chip clears it. Everything else sits under notes or the folded *More details*.

## What a visit adds

Things that change every visit live on `visit`, not on the pet: coat condition (0–5), shaved down, minutes, service, add-ons, and `behaviour_this_visit` (1–5, not captured yet). Features "as of the visit" = the visit row + the pet's values on that date, rebuilt from `pet_change`.

## Changing a list

1. Edit `pet_vocab.py` (codes) and `petVocab.ts` (words).
2. Add a migration that replaces the CHECK and maps existing values (see `c9d0e1f2a3b4_pet_profile_vocab.py`, which freezes its own copy of the SQL).
3. Note it here and in the CHANGELOG. Renaming a code changes the training data's meaning, so map old rows instead of leaving two spellings.
