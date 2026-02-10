import { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import { Play, Pause, Volume2, VolumeX, SkipBack, Lock } from 'lucide-react'

/**
 * CompactPlayer — 自定义音频播放器
 *
 * Props:
 *   - songId: string (网易云歌曲 ID)
 *   - title: string
 *   - artist: string
 *   - coverUrl: string | null
 *
 * Exposes audioRef via forwardRef for LyricsScroller sync.
 */
const CompactPlayer = forwardRef(function CompactPlayer({ songId, title, artist, coverUrl }, ref) {
  const audioRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.7)
  const [isMuted, setIsMuted] = useState(false)
  const [audioError, setAudioError] = useState(false)

  // 暴露 audioRef 给父组件
  useImperativeHandle(ref, () => audioRef.current)

  // 走后端代理，避免浏览器跨域/Referer 拦截
  const audioSrc = `/api/songs/${songId}/audio`

  const togglePlay = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play().catch(() => {})
    }
  }, [isPlaying])

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
    }
  }, [])

  const handleLoadedMetadata = useCallback(() => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration)
    }
  }, [])

  const handleSeek = useCallback((e) => {
    const time = parseFloat(e.target.value)
    if (audioRef.current) {
      audioRef.current.currentTime = time
      setCurrentTime(time)
    }
  }, [])

  const handleVolumeChange = useCallback((e) => {
    const v = parseFloat(e.target.value)
    setVolume(v)
    if (audioRef.current) {
      audioRef.current.volume = v
    }
    setIsMuted(v === 0)
  }, [])

  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }, [isMuted])

  const restart = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      setCurrentTime(0)
    }
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)
    const onEnded = () => { setIsPlaying(false); setCurrentTime(0) }
    const onError = () => setAudioError(true)

    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError)
    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)

    audio.volume = volume
    setAudioError(false)

    return () => {
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('error', onError)
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
    }
  }, [songId, handleTimeUpdate, handleLoadedMetadata, volume])

  const formatTime = (t) => {
    if (!t || isNaN(t)) return '0:00'
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] p-4">
      <audio ref={audioRef} src={audioSrc} preload="metadata" />

      {/* VIP / 不可播放提示 */}
      {audioError && (
        <div className="mb-3 flex items-center gap-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 px-3 py-2 text-xs text-yellow-400">
          <Lock size={12} />
          <span>该歌曲暂不可播放（可能是 VIP 专属）</span>
        </div>
      )}

      {/* Top: Cover + Info + Controls */}
      <div className="flex items-center gap-4">
        {/* Album Cover (spinning) */}
        <div className="relative shrink-0">
          <div
            className={`w-14 h-14 rounded-full overflow-hidden border-2 border-[var(--border-subtle)] ${
              isPlaying ? 'animate-spin-slow pulse-ring' : 'animate-spin-slow paused'
            }`}
          >
            {coverUrl ? (
              <img src={coverUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full bg-[var(--bg-elevated)] flex items-center justify-center">
                <span className="text-xs text-[var(--text-muted)]">♪</span>
              </div>
            )}
          </div>
        </div>

        {/* Song Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{title}</p>
          <p className="text-xs text-[var(--text-secondary)] truncate">{artist}</p>
        </div>

        {/* Play Controls */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={restart}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <SkipBack size={14} />
          </button>
          <button
            onClick={togglePlay}
            disabled={audioError}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors shadow-lg ${
              audioError
                ? 'bg-gray-600 cursor-not-allowed opacity-50'
                : 'bg-[var(--accent-pink)] hover:bg-[var(--accent-pink-dim)] shadow-[var(--accent-pink)]/20'
            }`}
          >
            {isPlaying ? (
              <Pause size={18} className="text-white" fill="white" />
            ) : (
              <Play size={18} className="text-white ml-0.5" fill="white" />
            )}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-[10px] text-[var(--text-muted)] w-10 text-right tabular-nums">
          {formatTime(currentTime)}
        </span>
        <div className="flex-1 relative">
          <div className="h-1 rounded-full bg-[var(--bg-elevated)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--accent-pink)] transition-[width] duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
        </div>
        <span className="text-[10px] text-[var(--text-muted)] w-10 tabular-nums">
          {formatTime(duration)}
        </span>
      </div>

      {/* Volume */}
      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={toggleMute}
          className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
        >
          {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={isMuted ? 0 : volume}
          onChange={handleVolumeChange}
          className="w-20 h-1"
        />
      </div>
    </div>
  )
})

export default CompactPlayer
