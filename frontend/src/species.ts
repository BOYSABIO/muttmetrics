export type Species = 'dog' | 'cat'

export function speciesLabel(species: string): string {
  if (species === 'cat') return 'Cat'
  if (species === 'dog') return 'Dog'
  return species
}
