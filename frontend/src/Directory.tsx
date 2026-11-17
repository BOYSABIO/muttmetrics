import { useEffect, useMemo, useState } from 'react'
import {
  errorMessage,
  fetchPetProfile,
  fetchOwnerProfile,
  createBreed,
  listBreeds,
  searchPets,
  type BreedListItem,
  type PetProfile,
  type Basic,
  type PetSearchItem,
  type OwnerProfile,
} from './api'
import { formatLastVisit } from './dates'
import { basicsLabel } from './petVocab'
import { withTransition } from './motion'
import { PetAvatar } from './PetAvatar'
import { PetProfileView } from './PetProfileView'
import type { SelectedPet } from './draft'
import { OwnerProfileView } from './OwnerProfileView'
import { speciesLabel } from './species'
import { ListSkeleton, SlowOverlay, Toast } from './ui'

type DirectoryProps = {
  onStartVisit?: (dog: SelectedPet) => void
}

/** Clients: searchable dog list, opening a dog or owner profile. */
export function Directory({ onStartVisit }: DirectoryProps) {
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PetSearchItem[]>([])
  const [breeds, setBreeds] = useState<BreedListItem[]>([])
  const [isBusy, setIsBusy] = useState(false)
  // Kept apart so the list never says "No clients yet" while it is loading
  // or after a failed load.
  const [listStatus, setListStatus] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )
  const [openPet, setOpenPet] = useState<PetProfile | null>(null)
  const [openOwner, setOpenOwner] = useState<OwnerProfile | null>(null)
  // The pet whose photo travels between its row and its profile (motion.css).
  const [morphPetId, setMorphPetId] = useState<number | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q === '') return results
    return results.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.owner_name.toLowerCase().includes(q),
    )
  }, [query, results])

  useEffect(() => {
    void (async () => {
      try {
        const [dogs, breedRows] = await Promise.all([searchPets(''), listBreeds()])
        setResults(dogs)
        setBreeds(breedRows)
        setListStatus('ready')
      } catch (error) {
        console.error(error)
        setListStatus('error')
        setMessage(errorMessage(error))
      }
    })()
  }, [])

  /** Reload the client list, e.g. after a rename, so Back shows fresh rows. */
  async function refreshList(): Promise<void> {
    try {
      setResults(await searchPets(''))
      setListStatus('ready')
    } catch (error) {
      console.error(error)
      setListStatus('error')
    }
  }

  async function openDirectoryPet(dogId: number): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    setMorphPetId(dogId)
    try {
      const profile = await fetchPetProfile(dogId)
      withTransition(() => {
        setOpenOwner(null)
        setOpenPet(profile)
        setMessage('')
      }, 'forward')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  async function openDirectoryOwner(ownerId: number): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    try {
      const profile = await fetchOwnerProfile(ownerId)
      withTransition(() => {
        setOpenPet(null)
        setOpenOwner(profile)
        setMessage('')
      }, 'forward')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  function closeProfiles(): void {
    withTransition(() => {
      setOpenPet(null)
      setOpenOwner(null)
      setMessage('')
    }, 'back')
  }

  const needBasics = filtered.filter((d) => d.basics_missing.length > 0).length

  const status = (
    <>
      <Toast message={message} onClear={() => setMessage('')} />
      <SlowOverlay active={isBusy} label="Opening" />
    </>
  )

  if (openPet !== null) {
    return (
      <>
        {status}
        <PetProfileView
          key={openPet.pet_id}
          profile={openPet}
          breeds={breeds}
          onBack={closeProfiles}
          onOpenOwner={(id) => void openDirectoryOwner(id)}
          onStartVisit={onStartVisit}
          onSaved={() => void refreshList()}
          onAddBreed={async (species, name) => {
            const breed = await createBreed(species, name)
            setBreeds((prev) =>
              prev.some((b) => b.breed_id === breed.breed_id) ? prev : [...prev, breed],
            )
            return breed
          }}
        />
      </>
    )
  }

  if (openOwner !== null) {
    return (
      <>
        {status}
        <OwnerProfileView
          key={openOwner.owner_id}
          profile={openOwner}
          onBack={closeProfiles}
          onOpenPet={(id) => void openDirectoryPet(id)}
          onSaved={() => void refreshList()}
        />
      </>
    )
  }

  return (
    <>
      {status}
      <section className="panel home-panel">
        <div className="search-bar">
          <label className="visually-hidden" htmlFor="directory_dog_search">
            Search clients
          </label>
          <input
            id="directory_dog_search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pets or owners…"
            autoComplete="off"
          />
        </div>
        {listStatus === 'loading' ? (
          <ListSkeleton rows={7} label="Loading clients…" />
        ) : listStatus === 'error' && results.length === 0 ? (
          <div className="empty-state">
            <p className="step-meta">Could not load clients.</p>
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setListStatus('loading')
                setMessage('')
                void refreshList()
              }}
            >
              Try again
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <p className="step-meta empty-state">
            {results.length === 0
              ? 'No clients yet — tap + to start a visit.'
              : 'No matches.'}
          </p>
        ) : (
          <>
            <div className="client-list-head" aria-hidden>
              <span>
                {filtered.length} {filtered.length === 1 ? 'pet' : 'pets'}
                {needBasics > 0 && (
                  <span className="client-list-need">
                    {' · '}
                    <BasicsPips missing={['size']} legend />
                    {needBasics} missing basics
                  </span>
                )}
              </span>
              <span>Last visit</span>
            </div>
            <ul className="dir-card-list client-list">
              {filtered.map((dog) => (
                <li key={dog.pet_id}>
                  {/* The whole row opens the dog for a mouse or a tap. The name
                      button is the keyboard / screen-reader way in, with its
                      own handler; the avatar is decoration. */}
                  <div
                    className={
                      isBusy && morphPetId === dog.pet_id
                        ? 'dir-card dir-card-row client-row is-opening'
                        : 'dir-card dir-card-row client-row'
                    }
                    onClick={() => {
                      if (!isBusy) void openDirectoryPet(dog.pet_id)
                    }}
                  >
                    <span
                      className="dir-card-avatar-hit"
                      aria-hidden="true"
                      style={
                        morphPetId === dog.pet_id ? { viewTransitionName: 'pet-avatar' } : undefined
                      }
                    >
                      <PetAvatar photoId={dog.avatar_photo_id} name={dog.name} thumb />
                    </span>
                    <div className="dir-card-body">
                      <span className="client-name-row">
                        <button
                          type="button"
                          className="dir-card-title-btn"
                          disabled={isBusy}
                          onClick={(e) => {
                            e.stopPropagation()
                            void openDirectoryPet(dog.pet_id)
                          }}
                        >
                          {dog.name}
                        </button>
                        <BasicsPips missing={dog.basics_missing} />
                      </span>
                      <div className="dir-card-meta">
                        {speciesLabel(dog.species)}
                        {' · '}
                        <button
                          type="button"
                          className="linkish"
                          disabled={isBusy}
                          onClick={(e) => {
                            e.stopPropagation()
                            void openDirectoryOwner(dog.owner_id)
                          }}
                        >
                          {dog.owner_name}
                        </button>
                      </div>
                    </div>
                    <span
                      className="client-last"
                      title={dog.last_visit_date ?? 'No visit date recorded'}
                    >
                      {formatLastVisit(dog.last_visit_date)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  )
}

/**
 * Four small squares after a pet's name, one per basic (breed, size, coat,
 * handling): filled when known, hollow when nobody has filled it in. Nothing
 * at all once all four are known, so a finished dog looks finished.
 */
function BasicsPips({ missing, legend = false }: { missing: Basic[]; legend?: boolean }) {
  if (missing.length === 0) return null
  const known = 4 - missing.length
  const label = legend ? undefined : `Basics ${known} of 4. Missing: ${basicsLabel(missing)}`
  return (
    <span
      className={legend ? 'basics-pips basics-pips-legend' : 'basics-pips'}
      role={legend ? undefined : 'img'}
      aria-label={label}
      title={label}
    >
      {(['breed', 'size', 'coat', 'handling'] as const).map((b) => (
        <i key={b} className={missing.includes(b) ? 'is-missing' : undefined} />
      ))}
    </span>
  )
}
