import { useState, useCallback } from 'react'
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

  const handleSearch = useCallback(async (query) => {
    setIsLoading(true)
    setHasSearched(true)
    setIntentType(null)
    setSearchParams({ q: query })

    try {
      const data = await searchSongs(query, 20)
      setResults(data.results || [])
      setIntentType(data.intent_type || null)
    } catch (err) {
      console.error('Search failed:', err)
      setResults([])
    } finally {
      setIsLoading(false)
    }
  }, [setSearchParams])

  // Auto-search from URL param on mount
  useState(() => {
    const q = searchParams.get('q')
    if (q) handleSearch(q)
  })

  return (
    <div className="gradient-mesh min-h-[calc(100vh-8rem)]">
      {/* Search Section */}
      <section className="max-w-7xl mx-auto px-6 pt-16 pb-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">语义搜索</h1>
          <p className="text-sm text-[var(--text-secondary)]">
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
      <section className="max-w-7xl mx-auto px-6 pb-20">
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mt-8">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-hidden animate-pulse">
                <div className="aspect-square bg-[var(--bg-elevated)]" />
                <div className="p-3.5 space-y-2">
                  <div className="h-4 bg-[var(--bg-elevated)] rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-elevated)] rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : results.length > 0 ? (
          <>
            <div className="flex items-center justify-between mt-8 mb-4">
              <p className="text-sm text-[var(--text-secondary)]">
                找到 <span className="text-[var(--accent-pink)] font-medium">{results.length}</span> 首匹配歌曲
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 stagger-children">
              {results.map((song, i) => (
                <SongCard key={song.id} song={song} index={i} />
              ))}
            </div>
          </>
        ) : hasSearched ? (
          <div className="text-center py-20">
            <SearchX size={48} className="mx-auto text-[var(--text-muted)] mb-4" />
            <p className="text-[var(--text-secondary)]">没有找到匹配的歌曲</p>
            <p className="text-sm text-[var(--text-muted)] mt-1">试试换个描述方式？</p>
          </div>
        ) : null}
      </section>
    </div>
  )
}
