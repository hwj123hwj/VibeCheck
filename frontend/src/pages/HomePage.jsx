import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Sparkles, Music, ArrowRight, PlayCircle } from 'lucide-react'
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
    <div className="gradient-mesh">
      {/* ── Hero Section ── */}
      <section className="page-container" style={{ paddingTop: '5rem', paddingBottom: '4rem', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
        {/* Soft Decorative Blobs */}
        <div style={{
          position: 'absolute', top: '-10%', left: '15%',
          width: 500, height: 500,
          background: 'rgba(255, 200, 87, 0.18)',
          borderRadius: '50%', filter: 'blur(100px)',
          zIndex: 0, animation: 'pulse 8s ease-in-out infinite',
        }} />
        <div style={{
          position: 'absolute', bottom: '-10%', right: '15%',
          width: 400, height: 400,
          background: 'rgba(255, 139, 167, 0.12)',
          borderRadius: '50%', filter: 'blur(80px)',
          zIndex: 0,
        }} />

        <div className="animate-fade-in-up page-container-narrow" style={{ position: 'relative', zIndex: 1 }}>
          {/* Badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.5rem 1.25rem',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.7)',
            border: '1px solid rgba(255, 139, 167, 0.15)',
            color: 'var(--text-secondary)',
            fontSize: '0.75rem',
            fontWeight: 500,
            marginBottom: '2rem',
            backdropFilter: 'blur(8px)',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <Sparkles size={14} style={{ color: 'var(--accent-pink)' }} />
            <span style={{ letterSpacing: '0.04em' }}>AI 驱动的沉浸式音乐探索</span>
          </div>

          {/* Main Title */}
          <h1 style={{
            fontSize: 'clamp(2.5rem, 6vw, 4.5rem)',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            lineHeight: 1.2,
            fontFamily: 'var(--font-serif)',
            color: 'var(--text-primary)',
            marginBottom: '1.5rem',
          }}>
            用{' '}
            <span style={{ position: 'relative', display: 'inline-block' }}>
              <span style={{
                position: 'relative', zIndex: 1,
                color: 'var(--accent-pink)',
                textShadow: '0 4px 20px rgba(255, 139, 167, 0.35)',
              }}>氛围</span>
              <svg style={{
                position: 'absolute', width: '100%', height: 10,
                bottom: -4, left: 0, zIndex: 0, opacity: 0.5,
              }} viewBox="0 0 100 10" preserveAspectRatio="none">
                <path d="M0 5 Q 50 10 100 5" stroke="var(--accent-yellow)" strokeWidth="8" fill="none" />
              </svg>
            </span>
            <br />
            寻找共鸣
          </h1>

          {/* Subtitle */}
          <p style={{
            fontSize: 'clamp(1rem, 2vw, 1.25rem)',
            color: 'var(--text-secondary)',
            lineHeight: 1.8,
            fontWeight: 300,
            maxWidth: '32rem',
            margin: '0 auto',
          }}>
            不必精确搜索。描述你的心情、场景或一句歌词碎片，
            VibeCheck 为你从 5 万首华语歌中捕获那份悸动。
          </p>

          {/* CTA Buttons */}
          <div style={{
            display: 'flex', flexWrap: 'wrap',
            alignItems: 'center', justifyContent: 'center',
            gap: '1rem', marginTop: '2.5rem',
          }}>
            <Link
              to="/search"
              className="group"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.625rem',
                padding: '0.875rem 2rem',
                borderRadius: 'var(--radius-full)',
                background: 'var(--text-primary)',
                color: 'white',
                fontWeight: 500,
                fontSize: '0.9375rem',
                textDecoration: 'none',
                transition: 'all 0.35s cubic-bezier(0.22, 1, 0.36, 1)',
                position: 'relative',
                overflow: 'hidden',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--accent-pink)'
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(255, 139, 167, 0.3)'
                e.currentTarget.style.transform = 'translateY(-2px)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--text-primary)'
                e.currentTarget.style.boxShadow = 'none'
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              <Music size={18} />
              开始探索
              <ArrowRight size={16} />
            </Link>
            
            <button 
              onClick={fetchRandom}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.875rem 2rem',
                borderRadius: 'var(--radius-full)',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                fontWeight: 500,
                fontSize: '0.9375rem',
                cursor: 'pointer',
                transition: 'all 0.3s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,139,167,0.3)'
                e.currentTarget.style.background = 'var(--accent-pink-light)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)'
                e.currentTarget.style.background = 'var(--bg-card)'
              }}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} style={{ color: loading ? 'var(--accent-pink)' : 'var(--text-muted)' }} />
              <span>随便听听</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── Discovery Grid ── */}
      <section className="page-container" style={{ paddingBottom: '4rem' }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
          marginBottom: '1.5rem', paddingBottom: '0.875rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <h2 style={{
            fontSize: '1.375rem',
            fontFamily: 'var(--font-serif)',
            fontWeight: 700,
            color: 'var(--text-primary)',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <PlayCircle size={22} style={{ color: 'var(--accent-pink)' }} />
            遇见 Vibe
          </h2>
          <p style={{
            fontSize: '0.6875rem',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontWeight: 500,
          }}>
            Daily Discovery
          </p>
        </div>

        {loading ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1.25rem',
          }}>
            {Array.from({ length: 12 }).map((_, i) => (
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
        ) : (
          <div className="stagger-children" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1.25rem',
          }}>
            {songs.map((song, i) => (
              <SongCard key={song.id} song={song} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}


