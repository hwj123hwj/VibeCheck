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
      className="group block rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-hidden hover:border-[var(--accent-pink)]/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-[var(--accent-pink)]/5"
    >
      {/* Cover Area */}
      <div className="relative aspect-square overflow-hidden bg-[var(--bg-elevated)]">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={song.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Disc3 size={48} className="text-[var(--text-muted)] opacity-30" />
          </div>
        )}

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-300 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-[var(--accent-pink)] flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-300 shadow-lg">
            <Play size={20} className="text-white ml-0.5" fill="white" />
          </div>
        </div>

        {/* Score badge (for search results) */}
        {song.score > 0 && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-[var(--accent-pink)]/90 text-xs font-medium text-white backdrop-blur-sm">
            {(song.score * 100).toFixed(0)}%
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3.5">
        <h3 className="text-sm font-semibold truncate text-[var(--text-primary)] group-hover:text-[var(--accent-pink)] transition-colors">
          {song.title}
        </h3>
        <p className="text-xs text-[var(--text-secondary)] mt-0.5 truncate">{song.artist}</p>

        {/* Vibe Tags */}
        {song.vibe_tags && song.vibe_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {song.vibe_tags.slice(0, 3).map((tag, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-[10px] bg-[var(--accent-pink)]/10 text-[var(--accent-pink)] border border-[var(--accent-pink)]/20"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Review snippet */}
        {song.review_text && (
          <p className="mt-2 text-[11px] text-[var(--text-muted)] line-clamp-2 leading-relaxed font-[var(--font-serif)]" style={{ fontFamily: 'var(--font-serif)' }}>
            {song.review_text}
          </p>
        )}
      </div>
    </Link>
  )
}
