import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Sparkles, Music, ArrowRight } from 'lucide-react'
import { getRandomSongs } from '../api/client'
import SongCard from '../components/SongCard'

export default function HomePage() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchRandom = async () => {
    setLoading(true)
    try {
      const data = await getRandomSongs(12)
      setSongs(data)
    } catch (err) {
      console.error('Failed to fetch random songs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRandom()
  }, [])

  return (
    <div className="gradient-mesh min-h-[calc(100vh-8rem)]">
      {/* ── Hero Section ── */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="animate-fade-in-up">
          {/* Brand */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[var(--accent-pink)]/10 border border-[var(--accent-pink)]/20 text-[var(--accent-pink)] text-xs font-medium mb-6">
            <Sparkles size={14} />
            基于 LLM 语义评语 · 混合推荐系统
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight">
            用<span className="text-[var(--accent-pink)] text-glow-pink">氛围</span>
            <br className="md:hidden" />找音乐
          </h1>

          <p className="mt-4 text-lg text-[var(--text-secondary)] max-w-md mx-auto leading-relaxed">
            不必精确搜索。描述你的心情、场景或一句歌词碎片，
            <br className="hidden md:block" />
            AI 为你从 5 万首华语歌中找到共鸣。
          </p>

          <Link
            to="/search"
            className="inline-flex items-center gap-2 mt-8 px-6 py-3 rounded-xl bg-[var(--accent-pink)] hover:bg-[var(--accent-pink-dim)] text-white font-medium transition-colors shadow-lg shadow-[var(--accent-pink)]/20"
          >
            <Music size={18} />
            开始探索
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* ── Vibe 壁放 (Random Discovery) ── */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold">Vibe 壁放</h2>
            <p className="text-sm text-[var(--text-muted)] mt-0.5">随机发现，遇见意外的共鸣</p>
          </div>
          <button
            onClick={fetchRandom}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)] hover:text-[var(--accent-pink)] hover:border-[var(--accent-pink)]/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            换一批
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-hidden animate-pulse">
                <div className="aspect-square bg-[var(--bg-elevated)]" />
                <div className="p-3.5 space-y-2">
                  <div className="h-4 bg-[var(--bg-elevated)] rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-elevated)] rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4 stagger-children">
            {songs.map((song, i) => (
              <SongCard key={song.id} song={song} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
