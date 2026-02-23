import { Link } from 'react-router-dom'
import { Play, Disc3 } from 'lucide-react'

/**
 * SongCard — 歌曲卡片 (首页/搜索结果通用)
 *
 * Props:
 *   - song: { id, title, artist, album_cover, vibe_tags?, review_text?, core_lyrics?, score? }
 *   - index: number (用于 stagger 动画)
 */
export default function SongCard({ song, index = 0 }) {
  const coverUrl = song.album_cover || null

  return (
    <Link
      to={`/song/${song.id}`}
      className="group card-soft"
      style={{
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 'var(--radius-xl)',
        overflow: 'hidden',
        height: '100%',
        textDecoration: 'none',
        color: 'inherit',
      }}
    >
      {/* Cover Area */}
      <div style={{ position: 'relative', aspectRatio: '1', overflow: 'hidden', background: 'var(--bg-secondary)' }}>
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={song.title}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transition: 'transform 0.7s ease-out',
            }}
            className="group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, var(--bg-secondary), var(--bg-elevated))',
          }}>
            <Disc3 size={40} style={{ color: 'var(--text-muted)', opacity: 0.2 }} />
          </div>
        )}

        {/* Hover Play Overlay */}
        <div
          className="group-hover:opacity-100"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: 0,
            transition: 'opacity 0.3s',
            background: 'rgba(0,0,0,0.15)',
          }}
        >
          <div style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: 'var(--accent-pink)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-pink)',
            transform: 'scale(0.9)',
            transition: 'transform 0.3s',
          }}
            className="group-hover:scale-100"
          >
            <Play size={20} color="white" fill="white" style={{ marginLeft: 2 }} />
          </div>
        </div>

        {/* Score badge (search results) */}
        {song.score > 0 && (
          <div style={{
            position: 'absolute',
            top: 8,
            right: 8,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 139, 167, 0.9)',
            fontSize: '0.7rem',
            fontWeight: 700,
            color: 'white',
            backdropFilter: 'blur(4px)',
          }}>
            {(song.score * 100).toFixed(0)}%
          </div>
        )}
      </div>

      {/* Info — generous padding to avoid text clipping */}
      <div style={{
        padding: '0.875rem 1rem 1rem',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
      }}>
        <h3
          className="group-hover:text-[var(--accent-pink)]"
          style={{
            fontSize: '0.875rem',
            fontWeight: 700,
            fontFamily: 'var(--font-serif)',
            letterSpacing: '-0.01em',
            lineHeight: 1.4,
            color: 'var(--text-primary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            transition: 'color 0.3s',
          }}
        >
          {song.title}
        </h3>
        <p style={{
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          fontWeight: 500,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {song.artist}
        </p>

        {/* Vibe Tags */}
        {song.vibe_tags && song.vibe_tags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginTop: '0.5rem' }}>
            {song.vibe_tags.slice(0, 3).map((tag, i) => (
              <span
                key={i}
                style={{
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.625rem',
                  fontWeight: 600,
                  letterSpacing: '0.04em',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-secondary)',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Review snippet */}
        {song.review_text && (
          <div style={{
            marginTop: '0.5rem',
            paddingTop: '0.5rem',
            borderTop: '1px solid var(--border-subtle)',
          }}>
            <p style={{
              fontSize: '0.6875rem',
              color: 'var(--text-muted)',
              lineHeight: 1.6,
              fontStyle: 'italic',
              fontFamily: 'var(--font-serif)',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              "{song.review_text}"
            </p>
          </div>
        )}

        {/* Explainability — 三路匹配度 */}
        {song.review_score != null && (
          <div style={{
            marginTop: '0.5rem',
            paddingTop: '0.5rem',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '3px',
          }}>
            <ScoreBar label="评语语义" value={song.review_score} color="var(--accent-pink)" />
            <ScoreBar label="歌词语义" value={song.lyrics_score} color="var(--accent-yellow)" />
            <ScoreBar label="关键词" value={song.rational_score} color="#8EC5FC" />
          </div>
        )}
      </div>
    </Link>
  )
}

/**
 * ScoreBar — 迷你进度条，展示单路匹配分数
 */
function ScoreBar({ label, value, color }) {
  const pct = Math.min(Math.round((value || 0) * 100), 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
      <span style={{
        fontSize: '0.575rem',
        color: 'var(--text-muted)',
        minWidth: '3rem',
        textAlign: 'right',
        flexShrink: 0,
      }}>
        {label}
      </span>
      <div style={{
        flex: 1,
        height: 4,
        borderRadius: 2,
        background: 'var(--bg-secondary)',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          borderRadius: 2,
          background: color,
          transition: 'width 0.6s ease-out',
        }} />
      </div>
      <span style={{
        fontSize: '0.55rem',
        color: 'var(--text-muted)',
        minWidth: '1.75rem',
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {pct}%
      </span>
    </div>
  )
}

