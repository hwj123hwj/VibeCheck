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
        // 并行请求：详情 + LRC + 推荐
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

  // Scroll to top on song change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [id])

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[var(--accent-pink)]" />
      </div>
    )
  }

  if (!song) {
    return (
      <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center gap-4">
        <p className="text-[var(--text-secondary)]">歌曲未找到</p>
        <Link to="/" className="text-sm text-[var(--accent-pink)] hover:underline">
          返回首页
        </Link>
      </div>
    )
  }

  return (
    <div className="gradient-mesh min-h-[calc(100vh-8rem)]">
      <div className="max-w-5xl mx-auto px-6 pt-8 pb-20">
        {/* Back Button */}
        <Link
          to={-1}
          onClick={(e) => { e.preventDefault(); window.history.back() }}
          className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors mb-6"
        >
          <ArrowLeft size={16} />
          返回
        </Link>

        {/* ── Main Content Grid ── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Left: Cover + Player + Info (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Album Cover */}
            <div className="relative aspect-square rounded-2xl overflow-hidden bg-[var(--bg-card)] border border-[var(--border-subtle)] shadow-2xl">
              {song.album_cover ? (
                <img
                  src={song.album_cover}
                  alt={song.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-[var(--bg-elevated)]">
                  <span className="text-6xl opacity-20">♪</span>
                </div>
              )}
              {/* Gradient overlay at bottom */}
              <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[var(--bg-primary)]/80 to-transparent" />
            </div>

            {/* Song Meta */}
            <div>
              <h1 className="text-2xl font-bold">{song.title}</h1>
              <p className="text-[var(--text-secondary)] mt-1">{song.artist}</p>
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
              <div>
                <h3 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Tag size={12} />
                  氛围标签
                </h3>
                <div className="flex flex-wrap gap-2">
                  {song.vibe_tags.map((tag, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-full text-xs bg-[var(--accent-pink)]/10 text-[var(--accent-pink)] border border-[var(--accent-pink)]/20"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Recommend Scene */}
            {song.recommend_scene && (
              <div>
                <h3 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <MapPin size={12} />
                  推荐场景
                </h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed" style={{ fontFamily: 'var(--font-serif)' }}>
                  {song.recommend_scene}
                </p>
              </div>
            )}
          </div>

          {/* Right: Lyrics + Radar + Review (3 cols) */}
          <div className="lg:col-span-3 space-y-6">
            {/* Lyrics Scroller */}
            <div className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-hidden">
              <div className="px-4 pt-4 pb-2 border-b border-[var(--border-subtle)]">
                <h3 className="text-sm font-medium text-[var(--text-secondary)]">歌词</h3>
              </div>
              <LyricsScroller
                lyrics={lrcLines}
                audioRef={playerRef}
              />
            </div>

            {/* Radar Chart + Review side-by-side on wider screens */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Radar Chart */}
              {song.vibe_scores && (
                <div className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] p-4">
                  <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">情感雷达</h3>
                  <VibeRadarChart scores={song.vibe_scores} />
                </div>
              )}

              {/* AI Review */}
              {song.review_text && (
                <div className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] p-5">
                  <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">AI 评语</h3>
                  <p
                    className="text-sm text-[var(--text-primary)] leading-relaxed"
                    style={{ fontFamily: 'var(--font-serif)' }}
                  >
                    {song.review_text}
                  </p>
                </div>
              )}
            </div>

            {/* Core Lyrics */}
            {song.core_lyrics && (
              <div className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] p-5">
                <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">精华歌词</h3>
                <blockquote
                  className="text-sm text-[var(--text-primary)]/80 leading-loose border-l-2 border-[var(--accent-pink)]/40 pl-4 whitespace-pre-line"
                  style={{ fontFamily: 'var(--font-serif)' }}
                >
                  {song.core_lyrics}
                </blockquote>
              </div>
            )}
          </div>
        </div>

        {/* ── Similar Recommendations ── */}
        {recommendations.length > 0 && (
          <section className="mt-16">
            <h2 className="text-xl font-bold mb-1">相似推荐</h2>
            <p className="text-sm text-[var(--text-muted)] mb-6">基于评语向量 + 歌词向量的混合融合</p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 stagger-children">
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
