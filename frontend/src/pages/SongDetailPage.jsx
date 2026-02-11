import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Tag, MapPin, Loader2 } from 'lucide-react'
import { getSongDetail, getSongLrc, getRecommendations } from '../api/client'
import { parseLrc } from '../utils/parseLrc'
import CompactPlayer from '../components/CompactPlayer'
import LyricsScroller from '../components/LyricsScroller'
import VibeRadarChart from '../components/VibeRadarChart'
import SongCard from '../components/SongCard'

export default function SongDetailPage() {
  const { id } = useParams()
  const playerRef = useRef(null)

  const [song, setSong] = useState(null)
  const [lrcLines, setLrcLines] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setSong(null)
      setLrcLines([])
      setRecommendations([])
      try {
        const [detail, lrc, rec] = await Promise.allSettled([
          getSongDetail(id),
          getSongLrc(id),
          getRecommendations(id, 6),
        ])
        if (cancelled) return
        if (detail.status === 'fulfilled') setSong(detail.value)
        if (lrc.status === 'fulfilled') setLrcLines(parseLrc(lrc.value.lrc))
        if (rec.status === 'fulfilled') setRecommendations(rec.value.recommendations || [])
      } catch (err) {
        console.error('Failed to load song:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [id])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [id])

  if (loading) {
    return (
      <div style={{ minHeight: 'calc(100vh - 8rem)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" style={{ color: 'var(--accent-pink)' }} />
      </div>
    )
  }

  if (!song) {
    return (
      <div style={{ minHeight: 'calc(100vh - 8rem)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
        <p style={{ color: 'var(--text-secondary)' }}>歌曲未找到</p>
        <Link to="/" style={{ fontSize: '0.875rem', color: 'var(--accent-pink)', textDecoration: 'none' }}>
          返回首页
        </Link>
      </div>
    )
  }

  return (
    <div className="gradient-mesh" style={{ minHeight: 'calc(100vh - 8rem)' }}>
      <div className="page-container" style={{ maxWidth: '64rem', paddingTop: '2rem', paddingBottom: '5rem' }}>
        {/* Back Button */}
        <Link
          to={-1}
          onClick={(e) => { e.preventDefault(); window.history.back() }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
            fontSize: '0.875rem', color: 'var(--text-secondary)',
            textDecoration: 'none', marginBottom: '1.5rem',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
        >
          <ArrowLeft size={16} />
          返回
        </Link>

        {/* ── Main Content Grid ── */}
        <div className="detail-grid" style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 3fr)',
          gap: '2.5rem',
        }}>
          {/* Left: Cover + Player + Info */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Album Cover */}
            <div style={{
              position: 'relative', aspectRatio: '1', borderRadius: 'var(--radius-xl)',
              overflow: 'hidden', background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              boxShadow: 'var(--shadow-lg)',
            }}>
              {song.album_cover ? (
                <img src={song.album_cover} alt={song.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-elevated)' }}>
                  <span style={{ fontSize: '4rem', opacity: 0.15 }}>♪</span>
                </div>
              )}
              <div style={{
                position: 'absolute', left: 0, right: 0, bottom: 0, height: '33%',
                background: 'linear-gradient(to top, rgba(255,252,245,0.8), transparent)',
              }} />
            </div>

            {/* Song Meta */}
            <div style={{ padding: '0 0.25rem' }}>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-serif)' }}>{song.title}</h1>
              <p style={{ color: 'var(--text-secondary)', marginTop: '0.375rem', fontSize: '0.9375rem' }}>{song.artist}</p>
            </div>

            {/* Player */}
            <CompactPlayer
              ref={playerRef}
              songId={id}
              title={song.title}
              artist={song.artist}
              coverUrl={song.album_cover}
            />

            {/* Vibe Tags */}
            {song.vibe_tags && song.vibe_tags.length > 0 && (
              <div style={{ padding: '0 0.25rem' }}>
                <h3 style={{
                  fontSize: '0.6875rem', color: 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                  marginBottom: '0.625rem', display: 'flex', alignItems: 'center', gap: '0.375rem',
                }}>
                  <Tag size={12} />
                  氛围标签
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {song.vibe_tags.map((tag, i) => (
                    <span key={i} style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.75rem',
                      background: 'var(--accent-pink-light)',
                      color: 'var(--accent-pink)',
                      border: '1px solid rgba(255, 139, 167, 0.2)',
                    }}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Recommend Scene */}
            {song.recommend_scene && (
              <div style={{ padding: '0 0.25rem' }}>
                <h3 style={{
                  fontSize: '0.6875rem', color: 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                  marginBottom: '0.625rem', display: 'flex', alignItems: 'center', gap: '0.375rem',
                }}>
                  <MapPin size={12} />
                  推荐场景
                </h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7, fontFamily: 'var(--font-serif)' }}>
                  {song.recommend_scene}
                </p>
              </div>
            )}
          </div>

          {/* Right: Lyrics + Radar + Review */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Lyrics Scroller */}
            <div style={{
              borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)', overflow: 'hidden',
            }}>
              <div style={{
                padding: '1rem 1.25rem 0.625rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>歌词</h3>
              </div>
              <LyricsScroller lyrics={lrcLines} audioRef={playerRef} />
            </div>

            {/* Radar Chart + Review */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem' }}>
              {song.vibe_scores && (
                <div style={{
                  borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)', padding: '1.25rem',
                }}>
                  <h3 style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.625rem' }}>情感雷达</h3>
                  <VibeRadarChart scores={song.vibe_scores} />
                </div>
              )}
              {song.review_text && (
                <div style={{
                  borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)', padding: '1.5rem',
                }}>
                  <h3 style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>AI 评语</h3>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: 1.8, fontFamily: 'var(--font-serif)' }}>
                    {song.review_text}
                  </p>
                </div>
              )}
            </div>

            {/* Core Lyrics */}
            {song.core_lyrics && (
              <div style={{
                borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)', padding: '1.5rem',
              }}>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>精华歌词</h3>
                <blockquote style={{
                  fontSize: '0.875rem', color: 'var(--text-primary)',
                  lineHeight: 2, borderLeft: '2px solid rgba(255, 139, 167, 0.4)',
                  paddingLeft: '1rem', whiteSpace: 'pre-line',
                  fontFamily: 'var(--font-serif)', opacity: 0.85,
                }}>
                  {song.core_lyrics}
                </blockquote>
              </div>
            )}
          </div>
        </div>

        {/* ── Similar Recommendations ── */}
        {recommendations.length > 0 && (
          <section style={{ marginTop: '4rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-serif)', marginBottom: '0.375rem' }}>相似推荐</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>基于评语向量 + 歌词向量的混合融合</p>
            <div className="stagger-children" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: '1rem',
            }}>
              {recommendations.map((song, i) => (
                <SongCard key={song.id} song={song} index={i} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
