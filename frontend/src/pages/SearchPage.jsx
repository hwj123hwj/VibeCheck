import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SearchX } from 'lucide-react'
import SearchInput from '../components/SearchInput'
import SongCard from '../components/SongCard'
import { searchSongs } from '../api/client'

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [results, setResults] = useState([])
  const [intentType, setIntentType] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Track the latest search to ignore stale responses
  const searchIdRef = useRef(0)

  const handleSearch = useCallback(async (query) => {
    const thisSearchId = ++searchIdRef.current

    setIsLoading(true)
    setHasSearched(true)
    setIntentType(null)
    setSearchParams({ q: query }, { replace: true })

    try {
      const data = await searchSongs(query, 20)
      // Only update if this is still the latest search
      if (searchIdRef.current !== thisSearchId) return
      setResults(data.results || [])
      setIntentType(data.intent_type || null)
    } catch (err) {
      if (searchIdRef.current !== thisSearchId) return
      console.error('Search failed:', err)
      setResults([])
    } finally {
      if (searchIdRef.current === thisSearchId) {
        setIsLoading(false)
      }
    }
  }, [setSearchParams])

  // Auto-search from URL param on mount (replaces the broken useState hack)
  const didAutoSearch = useRef(false)
  useEffect(() => {
    if (didAutoSearch.current) return
    const q = searchParams.get('q')
    if (q) {
      didAutoSearch.current = true
      handleSearch(q)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="gradient-mesh" style={{ minHeight: 'calc(100vh - 8rem)' }}>
      {/* Search Section */}
      <section className="page-container" style={{ paddingTop: '3.5rem', paddingBottom: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            fontFamily: 'var(--font-serif)',
            color: 'var(--text-primary)',
            marginBottom: '0.5rem',
          }}>
            语义搜索
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            描述心情、粘贴歌词、或直接搜歌名
          </p>
        </div>
        <SearchInput
          onSearch={handleSearch}
          isLoading={isLoading}
          intentType={intentType}
        />
      </section>

      {/* Results */}
      <section className="page-container" style={{ paddingBottom: '4rem' }}>
        {isLoading ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1.25rem',
            marginTop: '2rem',
          }}>
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} style={{
                borderRadius: 'var(--radius-xl)',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                overflow: 'hidden',
              }}>
                <div style={{ aspectRatio: '1', background: 'var(--bg-secondary)' }} className="animate-pulse" />
                <div style={{ padding: '0.875rem 1rem' }}>
                  <div style={{ height: 14, background: 'var(--bg-secondary)', borderRadius: 4, width: '75%', marginBottom: 8 }} className="animate-pulse" />
                  <div style={{ height: 12, background: 'var(--bg-secondary)', borderRadius: 4, width: '50%' }} className="animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : results.length > 0 ? (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              marginTop: '2rem', marginBottom: '1rem',
            }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                找到 <span style={{ color: 'var(--accent-pink)', fontWeight: 500 }}>{results.length}</span> 首匹配歌曲
              </p>
            </div>
            <div className="stagger-children" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
              gap: '1.25rem',
            }}>
              {results.map((song, i) => (
                <SongCard key={song.id} song={song} index={i} />
              ))}
            </div>
          </>
        ) : hasSearched ? (
          <div style={{ textAlign: 'center', padding: '5rem 0' }}>
            <SearchX size={48} style={{ margin: '0 auto 1rem', color: 'var(--text-muted)' }} />
            <p style={{ color: 'var(--text-secondary)' }}>没有找到匹配的歌曲</p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>试试换个描述方式？</p>
          </div>
        ) : null}
      </section>
    </div>
  )
}
