import { useEffect, useMemo, useState } from 'react'
import {
  errorMessage,
  fetchDogProfile,
  fetchOwnerProfile,
  listBreeds,
  searchDogs,
  type BreedListItem,
  type DogProfile,
  type DogSearchItem,
  type OwnerProfile,
} from './api'
import { formatLastVisit } from './dates'
import { DogAvatar } from './DogAvatar'
import { DogProfileView } from './DogProfileView'
import type { SelectedDog } from './draft'
import { OwnerProfileView } from './OwnerProfileView'

type DirectoryProps = {
  onStartVisit?: (dog: SelectedDog) => void
}

/** Clients: searchable dog list, opening a dog or owner profile. */
export function Directory({ onStartVisit }: DirectoryProps) {
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DogSearchItem[]>([])
  const [breeds, setBreeds] = useState<BreedListItem[]>([])
  const [isBusy, setIsBusy] = useState(false)
  // Kept apart so the list never says "No clients yet" while it is loading
  // or after a failed load.
  const [listStatus, setListStatus] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )
  const [openDog, setOpenDog] = useState<DogProfile | null>(null)
  const [openOwner, setOpenOwner] = useState<OwnerProfile | null>(null)

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
        const [dogs, breedRows] = await Promise.all([searchDogs(''), listBreeds()])
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
      setResults(await searchDogs(''))
      setListStatus('ready')
    } catch (error) {
      console.error(error)
      setListStatus('error')
    }
  }

  async function openDirectoryDog(dogId: number): Promise<void> {
    if (isBusy) return
    setIsBusy(true)
    setMessage('Loading…')
    try {
      const profile = await fetchDogProfile(dogId)
      setOpenOwner(null)
      setOpenDog(profile)
      setMessage('')
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
    setMessage('Loading…')
    try {
      const profile = await fetchOwnerProfile(ownerId)
      setOpenDog(null)
      setOpenOwner(profile)
      setMessage('')
    } catch (error) {
      console.error(error)
      setMessage(errorMessage(error))
    } finally {
      setIsBusy(false)
    }
  }

  function closeProfiles(): void {
    setOpenDog(null)
    setOpenOwner(null)
    setMessage('')
  }

  const status =
    message !== '' ? (
      <p className="status" role="status">
        {message}
      </p>
    ) : null

  if (openDog !== null) {
    return (
      <>
        {status}
        <DogProfileView
          key={openDog.dog_id}
          profile={openDog}
          breeds={breeds}
          onBack={closeProfiles}
          onOpenOwner={(id) => void openDirectoryOwner(id)}
          onStartVisit={onStartVisit}
          onSaved={() => void refreshList()}
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
          onOpenDog={(id) => void openDirectoryDog(id)}
          onSaved={() => void refreshList()}
        />
      </>
    )
  }

  return (
    <>
      {message !== '' && (
        <p className="status" role="status">
          {message}
        </p>
      )}
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
            placeholder="Search dogs or owners…"
            autoComplete="off"
          />
        </div>
        {listStatus === 'loading' ? (
          <p className="step-meta empty-state">Loading clients…</p>
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
                {filtered.length} {filtered.length === 1 ? 'dog' : 'dogs'}
              </span>
              <span>Last visit</span>
            </div>
            <ul className="dir-card-list client-list">
              {filtered.map((dog) => (
                <li key={dog.dog_id}>
                  {/* The whole row opens the dog for a mouse or a tap. The name
                      button is the keyboard / screen-reader way in, with its
                      own handler; the avatar is decoration. */}
                  <div
                    className="dir-card dir-card-row client-row"
                    onClick={() => {
                      if (!isBusy) void openDirectoryDog(dog.dog_id)
                    }}
                  >
                    <span className="dir-card-avatar-hit" aria-hidden="true">
                      <DogAvatar photoId={null} name={dog.name} />
                    </span>
                    <div className="dir-card-body">
                      <button
                        type="button"
                        className="dir-card-title-btn"
                        disabled={isBusy}
                        onClick={(e) => {
                          e.stopPropagation()
                          void openDirectoryDog(dog.dog_id)
                        }}
                      >
                        {dog.name}
                      </button>
                      <div className="dir-card-meta">
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
