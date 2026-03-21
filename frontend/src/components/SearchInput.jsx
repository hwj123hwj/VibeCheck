import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Sparkles, Loader2, ChevronDown } from 'lucide-react'

/**
 * SearchInput — 集成 LLM 意图解析动画的搜索框
 *
 * Props:
 *   - onSearch: (query: string, mode: string) => void
 *   - isLoading: boolean
 *   - intentType: string | null  ("vibe" | "lyrics" | "exact")
 */
export default function SearchInput({ onSearch, isLoading = false, intentType = null }) {
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [mode, setMode] = useState('auto')
  const inputRef = useRef(null)

  // 同步 URL params
  useEffect(() => {
    const q = searchParams.get('q')
    if (q) setQuery(q)
  }, [searchParams])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !isLoading) {
      onSearch(query.trim(), mode)
    }
  }

  const MODES = [
    { key: 'auto',   label: '自动识别', placeholder: '描述心情、粘贴歌词、或直接搜歌名…', hint: 'LLM 正在解析你的意图…' },
    { key: 'vibe',   label: '心情氛围', placeholder: '描述你现在的心情或场景…',           hint: '向量语义检索中…' },
    { key: 'lyrics', label: '搜歌词',   placeholder: '粘贴一段你记得的歌词…',             hint: '歌词语义匹配中…' },
    { key: 'title',  label: '搜歌名',   placeholder: '输入歌曲名…',                       hint: '歌名匹配中…' },
    { key: 'artist', label: '搜歌手',   placeholder: '输入歌手名…',                       hint: '歌手匹配中…' },
  ]

  const currentMode = MODES.find(m => m.key === mode) || MODES[0]

  const intentLabels = {
    vibe:   '心情氛围',
    lyrics: '搜歌词',
    exact:  '搜歌名',
    auto:   '自动识别',
    title:  '搜歌名',
    artist: '搜歌手',
  }

  // Example prompts
  const examples = [
    '深夜一个人emo的时候听什么',
    '后来我总算学会了如何去爱',
    '周杰伦 晴天',
    '适合开车兜风的歌',
    '失恋后想大哭一场',
  ]

  const handleExample = (text) => {
    setQuery(text)
    onSearch(text, mode)
  }

  return (
    <div style={{ width: '100%', maxWidth: '42rem', marginLeft: 'auto', marginRight: 'auto' }}>
      {/* Search Bar */}
      <form onSubmit={handleSubmit} style={{ position: 'relative' }}>
        <div style={{ position: 'relative' }}>

          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            transition: 'border-color 0.3s, box-shadow 0.3s',
          }}>
            {/* 左侧模式下拉框 */}
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              flexShrink: 0,
              borderRight: '1px solid var(--border-subtle)',
              height: '100%',
            }}>
              <select
                value={mode}
                onChange={e => setMode(e.target.value)}
                disabled={isLoading}
                style={{
                  appearance: 'none',
                  WebkitAppearance: 'none',
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  padding: '0 2rem 0 0.875rem',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  color: 'var(--accent-pink)',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  height: '100%',
                  minWidth: '5.5rem',
                }}
              >
                {MODES.map(m => (
                  <option key={m.key} value={m.key}>{m.label}</option>
                ))}
              </select>
              <ChevronDown size={13} style={{
                position: 'absolute',
                right: '0.5rem',
                pointerEvents: 'none',
                color: 'var(--accent-pink)',
                opacity: 0.7,
              }} />
            </div>

            {/* 搜索图标 */}
            <div style={{
              padding: '0 0.625rem 0 0.75rem',
              color: isLoading ? 'var(--accent-pink)' : 'var(--text-muted)',
              pointerEvents: 'none',
              display: 'flex',
              alignItems: 'center',
              flexShrink: 0,
            }}>
              {isLoading
                ? <Loader2 size={18} className="animate-spin" />
                : <Search size={18} />
              }
            </div>

            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={currentMode.placeholder}
              style={{
                flex: 1,
                paddingTop: '1rem',
                paddingBottom: '1rem',
                paddingRight: '0.5rem',
                background: 'transparent',
                color: 'var(--text-primary)',
                fontSize: '1rem',
                border: 'none',
                outline: 'none',
              }}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              style={{
                marginRight: '0.5rem',
                padding: '0.5rem 1.25rem',
                borderRadius: 'var(--radius-md)',
                background: isLoading || !query.trim() ? 'rgba(255,139,167,0.3)' : 'var(--accent-pink)',
                color: 'white',
                fontSize: '0.875rem',
                fontWeight: 500,
                border: 'none',
                cursor: isLoading || !query.trim() ? 'not-allowed' : 'pointer',
                transition: 'all 0.3s',
                flexShrink: 0,
              }}
              onMouseEnter={(e) => { if (!isLoading && query.trim()) e.currentTarget.style.background = 'var(--accent-pink-dim)' }}
              onMouseLeave={(e) => { if (!isLoading && query.trim()) e.currentTarget.style.background = 'var(--accent-pink)' }}
            >
              {isLoading ? '搜索中…' : '搜索'}
            </button>
          </div>
        </div>
      </form>

      {/* Intent Indicator */}
      {isLoading && (
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--accent-pink)' }} className="animate-pulse">
          <Sparkles size={14} />
          <span>{currentMode.hint}</span>
        </div>
      )}

      {intentType && !isLoading && (
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <Sparkles size={14} style={{ color: 'var(--accent-pink)' }} />
          <span>
            识别模式：
            <span style={{ color: 'var(--accent-pink)', fontWeight: 500, marginLeft: '0.25rem' }}>
              {intentLabels[intentType] || intentType}
            </span>
          </span>
        </div>
      )}

      {/* Example Prompts */}
      {!intentType && !isLoading && (
        <div style={{ marginTop: '1.25rem', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0.5rem' }}>
          {examples.map((text, i) => (
            <button
              key={i}
              onClick={() => handleExample(text)}
              style={{
                padding: '0.375rem 0.875rem',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.75rem',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--accent-pink)'
                e.currentTarget.style.borderColor = 'rgba(255,139,167,0.3)'
                e.currentTarget.style.background = 'var(--accent-pink-light)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--text-secondary)'
                e.currentTarget.style.borderColor = 'var(--border-subtle)'
                e.currentTarget.style.background = 'var(--bg-elevated)'
              }}
            >
              {text}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
