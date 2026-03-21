import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Tag, MapPin, Loader2, Play, Pause, SkipBack, Lock } from 'lucide-react'
import { getSongDetail, getSongLrc, getRecommendations } from '../api/client'
import { parseLrc } from '../utils/parseLrc'
import LyricsScroller from '../components/LyricsScroller'
import VibeRadarChart from '../components/VibeRadarChart'
import SongCard from '../components/SongCard'
import { usePlayer } from '../context/PlayerContext'

export default function SongDetailPage() {
  const { id } = useParams()
  const { loadSong, audioRef, isPlaying, togglePlay, audioError, currentSong } = usePlayer()

  const [song, setSong] = useState(null)
  const [lrcLines, setLrcLines] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [lrcLoading, setLrcLoading] = useState(true)
  const [recLoading, setRecLoading] = useState(true)
  const [recError, setRecError] = useState(false)
  const [wReview, setWReview] = useState(0.5)
  const [wLyrics, setWLyrics] = useState(0.4)
  const wTfidf = Math.max(0, parseFloat((1 - wReview - wLyrics).toFixed(2)))
  const [dedupe, setDedupe] = useState(false)

  useEffect(() => {
    let cancelled = false

    // 优先加载歌曲详情，详情到了立即渲染
    const loadDetail = async () => {
      setLoading(true)
      setSong(null)
      setLrcLines([])
      setRecommendations([])
      setLrcLoading(true)
      setRecLoading(true)
      setRecError(false)
      try {
        const detail = await getSongDetail(id)
        if (cancelled) return
        setSong(detail)
        // 加载到全局播放器，保持跨页面持续播放
        loadSong(detail)
      } catch (err) {
        console.error('Failed to load song detail:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    // LRC 和推荐完全独立加载，谁先回来谁先显示
    const loadLrc = async () => {
      try {
        const lrc = await getSongLrc(id)
        if (cancelled) return
        setLrcLines(parseLrc(lrc.lrc))
      } catch (err) {
        console.error('Failed to load lrc:', err)
      } finally {
        if (!cancelled) setLrcLoading(false)
      }
    }

    const loadRec = async (weights) => {
      try {
        const rec = await getRecommendations(id, 6, weights)
        if (cancelled) return
        setRecommendations(rec.recommendations || [])
      } catch (err) {
        console.error('Failed to load recommendations:', err)
        if (!cancelled) setRecError(true)
      } finally {
        if (!cancelled) setRecLoading(false)
      }
    }

    loadDetail()
    loadLrc()
    loadRec({})

    return () => { cancelled = true }
  }, [id])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [id])

  const handleRecommend = () => {
    const tfidf = Math.max(0, parseFloat((1 - wReview - wLyrics).toFixed(2)))
    setRecLoading(true)
    setRecError(false)
    setRecommendations([])
    let cancelled = false
    getRecommendations(id, 6, { w_review: wReview, w_lyrics: wLyrics, w_tfidf: tfidf }, dedupe)
      .then(rec => { if (!cancelled) setRecommendations(rec.recommendations || []) })
      .catch(err => { console.error(err); if (!cancelled) setRecError(true) })
      .finally(() => { if (!cancelled) setRecLoading(false) })
    return () => { cancelled = true }
  }

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

            {/* Player — 复用全局播放状态 */}
            <div style={{
              borderRadius: 'var(--radius-xl)',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              padding: '1rem',
              boxShadow: 'var(--shadow-sm)',
            }}>
              {audioError && (
                <div style={{
                  marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem',
                  borderRadius: 'var(--radius-sm)', background: 'var(--accent-yellow-light)',
                  border: '1px solid rgba(255, 200, 87, 0.3)',
                  padding: '0.5rem 0.75rem', fontSize: '0.75rem', color: '#B8860B',
                }}>
                  <Lock size={12} />
                  <span>VIP 专属歌曲，</span>
                  <a
                    href={`https://music.163.com/#/song?id=${id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: '#B8860B',
                      fontWeight: 600,
                      textDecoration: 'underline',
                      textUnderlineOffset: '2px',
                    }}
                  >
                    前往网易云开通会员收听 →
                  </a>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                  width: 56, height: 56, borderRadius: '50%', overflow: 'hidden', flexShrink: 0,
                  border: '2px solid var(--border-subtle)',
                  animation: isPlaying && currentSong?.id === id ? 'spin 8s linear infinite' : 'spin 8s linear infinite paused',
                }}>
                  {song.album_cover
                    ? <img src={song.album_cover} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    : <div style={{ width: '100%', height: '100%', background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ fontSize: '1rem', opacity: 0.3 }}>♪</span>
                      </div>
                  }
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: '0.875rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{song.title}</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{song.artist}</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                  <button
                    onClick={() => { if (audioRef.current) { audioRef.current.currentTime = 0 } }}
                    style={{ width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                  >
                    <SkipBack size={14} />
                  </button>
                  <button
                    onClick={togglePlay}
                    disabled={audioError}
                    style={{
                      width: 40, height: 40, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: audioError ? '#ccc' : 'var(--accent-pink)',
                      border: 'none',
                      cursor: audioError ? 'not-allowed' : 'pointer',
                      opacity: audioError ? 0.5 : 1,
                      boxShadow: audioError ? 'none' : 'var(--shadow-pink)',
                    }}
                  >
                    {isPlaying && currentSong?.id === id
                      ? <Pause size={18} color="white" fill="white" />
                      : <Play size={18} color="white" fill="white" style={{ marginLeft: 2 }} />
                    }
                  </button>
                </div>
              </div>
            </div>

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
              {lrcLoading
              ? <div style={{ height: '12rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Loader2 size={20} className="animate-spin" style={{ color: 'var(--accent-pink)', opacity: 0.5 }} />
                </div>
              : <LyricsScroller lyrics={lrcLines} audioRef={audioRef} />
            }
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
        {/* 权重调节面板 — 始终展示 */}
        <section style={{ marginTop: '4rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-serif)', marginBottom: '0.25rem' }}>相似推荐</h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>基于评语向量 + 歌词向量 + TF-IDF 的混合融合</p>

          <div style={{
            borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)', padding: '1.25rem 1.5rem',
            marginBottom: '1.5rem',
          }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
              权重调节
            </p>

            {/* w_review */}
            <div style={{ marginBottom: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>评语向量</span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--accent-pink)', fontVariantNumeric: 'tabular-nums' }}>{wReview.toFixed(2)}</span>
              </div>
              <input
                type="range" min={0} max={1} step={0.05}
                value={wReview}
                onChange={e => {
                  const v = parseFloat(e.target.value)
                  if (v + wLyrics > 1) return
                  setWReview(v)
                }}
                style={{ width: '100%', accentColor: 'var(--accent-pink)' }}
              />
            </div>

            {/* w_lyrics */}
            <div style={{ marginBottom: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>歌词向量</span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--accent-pink)', fontVariantNumeric: 'tabular-nums' }}>{wLyrics.toFixed(2)}</span>
              </div>
              <input
                type="range" min={0} max={1} step={0.05}
                value={wLyrics}
                onChange={e => {
                  const v = parseFloat(e.target.value)
                  if (wReview + v > 1) return
                  setWLyrics(v)
                }}
                style={{ width: '100%', accentColor: 'var(--accent-pink)' }}
              />
            </div>

            {/* w_tfidf 只读 */}
            <div style={{ marginBottom: '1.125rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>TF-IDF 关键词 <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>(自动)</span></span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>{wTfidf.toFixed(2)}</span>
              </div>
              <div style={{
                height: '4px', borderRadius: '2px',
                background: 'var(--border-subtle)', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', borderRadius: '2px',
                  width: `${wTfidf * 100}%`,
                  background: 'var(--text-muted)', opacity: 0.4,
                  transition: 'width 0.15s',
                }} />
              </div>
            </div>

            {/* 去重开关 */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              marginBottom: '0.875rem',
              padding: '0.625rem 0.75rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
            }}>
              <div>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>同名歌曲去重</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '0.375rem' }}>
                  {dedupe ? '每个歌名只保留最相似的一条' : '显示全部版本'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setDedupe(v => !v)}
                style={{
                  width: 36, height: 20, borderRadius: 10, border: 'none',
                  background: dedupe ? 'var(--accent-pink)' : 'var(--border-subtle)',
                  cursor: 'pointer', position: 'relative', transition: 'background 0.2s',
                  flexShrink: 0,
                }}
              >
                <span style={{
                  position: 'absolute', top: 3,
                  left: dedupe ? 18 : 3,
                  width: 14, height: 14, borderRadius: '50%',
                  background: 'white',
                  transition: 'left 0.2s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                }} />
              </button>
            </div>

            <button
              onClick={handleRecommend}
              disabled={recLoading}
              style={{
                width: '100%', padding: '0.5rem',
                borderRadius: 'var(--radius-lg)',
                background: recLoading ? 'var(--bg-elevated)' : 'var(--accent-pink)',
                color: recLoading ? 'var(--text-muted)' : 'white',
                border: 'none', cursor: recLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem', fontWeight: 600,
                transition: 'background 0.2s',
              }}
            >
              {recLoading ? '推荐中…' : '开始推荐'}
            </button>
          </div>
        </section>

        {recLoading && (
          <section style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Loader2 size={16} className="animate-spin" style={{ color: 'var(--accent-pink)', opacity: 0.5 }} />
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>加载相似推荐…</span>
          </section>
        )}
        {!recLoading && recError && (
          <section style={{ marginTop: '4rem' }}>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>推荐加载失败，请刷新页面重试。</p>
          </section>
        )}
        {!recLoading && recommendations.length > 0 && (
          <section>
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
