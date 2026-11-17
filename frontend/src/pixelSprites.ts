/**
 * The drawings for the two pixel dogs (0.8.0): one letter per square,
 * '.' is empty. Original art, kept as text so there are no image files.
 * How they are used: PixelDogs.tsx. Rules: ui-conventions.md ("The dogs").
 */

export type Frame = readonly string[]

export const COLOURS: Record<string, string> = {
  K: '#231d16', // black coat (the app's ink)
  G: '#4f4336', // lighter black: the edge of an ear
  M: '#3b3128', // a black dog's muzzle, just lighter than his coat
  H: '#8a7a68', // shine on a nose
  W: '#fffaf0', // white coat, and the glint in an eye
  D: '#e3d7c3', // white coat in shade
  L: '#dba6af', // pink skin on the nose bridge
  N: '#050403', // nose
  E: '#8a5526', // collie's eye
  A: '#b87a33', // guard's eye
  T: '#c98a45', // tan eyebrow dot
  P: '#e96f8b', // tongue
  p: '#c44f6c', // tongue tip
}

/** The same drawing with some rows swapped: a blink, a tail in another place. */
function withRows(frame: Frame, rows: Record<number, string>): Frame {
  return frame.map((line, i) => rows[i] ?? line)
}

// ---------------------------------------------------------------------------
// Front views, sitting (16 × 18)
// ---------------------------------------------------------------------------

/** Black and white, a blaze down the face, pink on the nose, tongue out. */
export const COLLIE: Frame = [
  '....KKKWWKKK....',
  '..KKKKKWWKKKKK..',
  '.KKKKKKWWKKKKKK.',
  'KKKKKKKWWKKKKKKK',
  'KKKEWKKWWKKEWKKK',
  'KKKKKKWWWWKKKKKK',
  'KKKKKWWLLWWKKKKK',
  'KKGKWWNHNNWWKGKK',
  'KGK.WWWNNWWW.KGK',
  '.K...WKPPKW...K.',
  '.....WWPPWW.....',
  '...KWWWPPWWWK...',
  '..KKWDWppWDWKK..',
  '.KKKWWDWWDWWKKK.',
  '.KKKKWWWWWWKKKK.',
  '.KKKWWWKKWWWKKK.',
  '.KKKWWWKKWWWKKK.',
  '..WWWWW..WWWWW..',
]

/** Mid-pant: the tongue a square longer, the ears a square lower. */
export const COLLIE_PANT: Frame = withRows(COLLIE, {
  8: 'KGKKWWWNNWWWKKGK',
  9: '.KK..WKPPKW..KK.',
  12: '..KKWDWPPWDWKK..',
  13: '.KKKWWDppDWWKKK.',
})

/** Black all over, with tan dots for eyebrows. */
export const GUARD: Frame = [
  '....KKKKKKKK....',
  '..KKKKKKKKKKKK..',
  '.KKKTKKKKKKTKKK.',
  'KKKKKKKKKKKKKKKK',
  'KKKAWKKKKKKAWKKK',
  'KKKKKKKKKKKKKKKK',
  'KKGKKKMMMMKKKGKK',
  'KGKKKMNHNNMKKKGK',
  'KGKKKMNNNNMKKKGK',
  'KKGKKKMNNMKKKGKK',
  '.KK..KGGGGK..KK.',
  '..KKKKKKKKKKKK..',
  '.KKKKKKKKKKKKKK.',
  '.KKKKKKKKKKKKKK.',
  '.KKKKKKKKKKKKKK.',
  '.KKKKGKKKKGKKKK.',
  '.KKKKGKKKKGKKKK.',
  '..KKKKK..KKKKK..',
]

export const GUARD_BLINK: Frame = withRows(GUARD, { 4: 'KKKGGKKKKKKGGKKK' })
/** A look to his right, at whoever is sitting next to him. */
export const GUARD_SIDE_EYE: Frame = withRows(GUARD, { 4: 'KKAWKKKKKKAWKKKK' })

// Tails (5 × 5), drawn beside the dog: one drawing with the tail up, one with
// it down. Swapping them is the wag. The same two are used when a dog sits
// and when only his head shows over an edge.
export const GUARD_TAIL_UP: Frame = ['...KK', '..KKK', '.KKK.', 'KKK..', 'KK...']
export const GUARD_TAIL_DOWN: Frame = ['.....', '.....', '..KKK', 'KKKKK', 'KKK..']
/** The collie's is on his other side and has a white tip. */
export const COLLIE_TAIL_UP: Frame = ['WW...', 'KKK..', '.KKK.', '..KKK', '...KK']
export const COLLIE_TAIL_DOWN: Frame = ['.....', '.....', 'WKK..', 'KKKKK', '..KKK']
