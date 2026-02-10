import { useState, useRef, useEffect, useCallback } from 'react'

/**
 * LyricsScroller — 歌词同步滚动组件
 *
 * Props:
 *   - lyrics: [{time, text}] 解析后的 LRC 数组
 *   - audioRef: React ref 指向 <audio> 元素
 */
export default function LyricsScroller({ lyrics, audioRef }) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const containerRef = useRef(null)
  const lineRefs = useRef([])

  // 根据 audio 当前时间查找激活行
  const handleTimeUpdate = useCallback(() => {
    const currentTime = audioRef.current?.currentTime ?? 0
    let idx = -1
    for (let i = lyrics.length - 1; i >= 0; i--) {
      if (currentTime >= lyrics[i].time) {
        idx = i
        break
      }
    }
    setActiveIndex(idx)
  }, [lyrics, audioRef])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.addEventListener('timeupdate', handleTimeUpdate)
    return () => audio.removeEventListener('timeupdate', handleTimeUpdate)
  }, [audioRef, handleTimeUpdate])

  // 自动滚动到高亮行 (居中)
  useEffect(() => {
    if (activeIndex < 0 || !lineRefs.current[activeIndex]) return
    lineRefs.current[activeIndex].scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }, [activeIndex])

  // 点击歌词跳转
  const handleLineClick = (time) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time
    }
  }

  if (!lyrics || lyrics.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-[var(--text-muted)] text-sm">
        暂无歌词
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="lyrics-container h-72 overflow-y-auto px-4 py-8"
    >
      {lyrics.map((line, i) => (
        <p
          key={`${i}-${line.time}`}
          ref={el => lineRefs.current[i] = el}
          onClick={() => handleLineClick(line.time)}
          className={`py-2.5 text-center transition-all duration-400 cursor-pointer select-none ${
            i === activeIndex
              ? 'text-[var(--text-primary)] text-base font-bold scale-105 text-glow-pink'
              : 'text-[var(--text-muted)] text-sm hover:text-[var(--text-secondary)]'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          {line.text}
        </p>
      ))}
    </div>
  )
}
