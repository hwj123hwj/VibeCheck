import { createContext, useContext, useRef, useState, useCallback } from 'react'

const PlayerContext = createContext(null)

/**
 * PlayerProvider — 全局播放器状态
 *
 * 持有唯一的 <audio> 元素，路由切换时不销毁，实现跨页面持续播放。
 */
export function PlayerProvider({ children }) {
  const audioRef = useRef(null)

  const [currentSong, setCurrentSong] = useState(null)
  // null = 未加载, true = 播放中, false = 暂停
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [audioError, setAudioError] = useState(false)
  const [volume, setVolumeState] = useState(0.7)
  const [isMuted, setIsMuted] = useState(false)

  /**
   * 加载一首新歌并自动播放
   * song: { id, title, artist, album_cover }
   */
  const loadSong = useCallback((song) => {
    const audio = audioRef.current
    if (!audio) return

    // 同一首歌不重新加载
    if (currentSong?.id === song.id) {
      if (!isPlaying) audio.play().catch(() => {})
      return
    }

    setCurrentSong(song)
    setAudioError(false)
    setCurrentTime(0)
    setDuration(0)
    setIsPlaying(false)

    audio.src = `/api/songs/${song.id}/audio`
    audio.load()
    audio.play().catch(() => {})
  }, [currentSong, isPlaying])

  const togglePlay = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !currentSong) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play().catch(() => {})
    }
  }, [isPlaying, currentSong])

  const seek = useCallback((time) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
    setCurrentTime(time)
  }, [])

  const setVolume = useCallback((v) => {
    const audio = audioRef.current
    if (!audio) return
    audio.volume = v
    setVolumeState(v)
    setIsMuted(v === 0)
  }, [])

  const toggleMute = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    const next = !isMuted
    audio.muted = next
    setIsMuted(next)
  }, [isMuted])

  const restart = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = 0
    setCurrentTime(0)
  }, [])

  // audio 事件处理器，挂到 <audio> 元素上
  const handlers = {
    onPlay: () => setIsPlaying(true),
    onPause: () => setIsPlaying(false),
    onEnded: () => { setIsPlaying(false); setCurrentTime(0) },
    onError: () => setAudioError(true),
    onTimeUpdate: () => setCurrentTime(audioRef.current?.currentTime ?? 0),
    onLoadedMetadata: () => {
      const audio = audioRef.current
      if (!audio) return
      setDuration(audio.duration)
      audio.volume = volume
    },
  }

  return (
    <PlayerContext.Provider value={{
      audioRef,
      currentSong,
      isPlaying,
      currentTime,
      duration,
      audioError,
      volume,
      isMuted,
      loadSong,
      togglePlay,
      seek,
      setVolume,
      toggleMute,
      restart,
    }}>
      {/* 唯一 audio 元素，常驻于 Provider 中，不随路由销毁 */}
      <audio
        ref={audioRef}
        preload="metadata"
        {...handlers}
      />
      {children}
    </PlayerContext.Provider>
  )
}

export function usePlayer() {
  return useContext(PlayerContext)
}
