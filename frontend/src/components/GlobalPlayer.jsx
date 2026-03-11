import { Play, Pause, SkipBack, Volume2, VolumeX, Music } from 'lucide-react'
import { usePlayer } from '../context/PlayerContext'

/**
 * GlobalPlayer — 常驻底部播放条
 *
 * 仅在有 currentSong 时显示。
 */
export default function GlobalPlayer() {
  const {
    currentSong,
    isPlaying,
    currentTime,
    duration,
    audioError,
    volume,
    isMuted,
    togglePlay,
    seek,
    setVolume,
    toggleMute,
    restart,
  } = usePlayer()

  if (!currentSong) return null

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  const formatTime = (t) => {
    if (!t || isNaN(t)) return '0:00'
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 100,
      background: 'rgba(255, 252, 245, 0.92)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderTop: '1px solid var(--border-subtle)',
      boxShadow: '0 -4px 24px rgba(0,0,0,0.06)',
    }}>
      {/* 进度条 — 贴顶部边缘 */}
      <div style={{ position: 'relative', height: 3, background: 'var(--bg-secondary)', cursor: 'pointer' }}>
        <div style={{
          width: `${progress}%`,
          height: '100%',
          background: 'var(--accent-pink)',
          transition: 'width 0.2s linear',
        }} />
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={currentTime}
          onChange={(e) => seek(parseFloat(e.target.value))}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            opacity: 0,
            cursor: 'pointer',
            margin: 0,
          }}
        />
      </div>

      <div style={{
        maxWidth: '64rem',
        margin: '0 auto',
        padding: '0.625rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
      }}>
        {/* 封面 + 歌曲信息 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: 0 }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
            flexShrink: 0,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-subtle)',
          }}>
            {currentSong.album_cover ? (
              <img
                src={currentSong.album_cover}
                alt={currentSong.title}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Music size={16} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
              </div>
            )}
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {currentSong.title}
            </p>
            <p style={{
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {currentSong.artist}
            </p>
          </div>
        </div>

        {/* 播放控制 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
          <button
            onClick={restart}
            style={{
              width: 32, height: 32, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--text-secondary)',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
          >
            <SkipBack size={16} />
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
              boxShadow: audioError ? 'none' : '0 2px 12px rgba(255, 139, 167, 0.4)',
              transition: 'all 0.2s',
            }}
          >
            {isPlaying
              ? <Pause size={18} color="white" fill="white" />
              : <Play size={18} color="white" fill="white" style={{ marginLeft: 2 }} />
            }
          </button>
        </div>

        {/* 时间 */}
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          fontVariantNumeric: 'tabular-nums',
          flexShrink: 0,
          display: 'flex',
          gap: '0.25rem',
        }}>
          <span>{formatTime(currentTime)}</span>
          <span>/</span>
          <span>{formatTime(duration)}</span>
        </div>

        {/* 音量 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
          <button
            onClick={toggleMute}
            style={{
              background: 'transparent', border: 'none',
              cursor: 'pointer', color: 'var(--text-muted)',
              display: 'flex', alignItems: 'center',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={isMuted ? 0 : volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            style={{ width: 72, cursor: 'pointer' }}
          />
        </div>
      </div>
    </div>
  )
}
