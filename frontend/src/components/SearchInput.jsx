import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Sparkles, Loader2 } from 'lucide-react'

/**
 * SearchInput — 集成 LLM 意图解析动画的搜索框
 *
 * Props:
 *   - onSearch: (query: string) => void
 *   - isLoading: boolean
 *   - intentType: string | null  ("vibe" | "lyrics" | "exact")
 */
export default function SearchInput({ onSearch, isLoading = false, intentType = null }) {
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const inputRef = useRef(null)

  // 同步 URL params
  useEffect(() => {
    const q = searchParams.get('q')
    if (q) setQuery(q)
  }, [searchParams])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !isLoading) {
      onSearch(query.trim())
    }
  }

  const intentLabels = {
    vibe: '氛围感知',
    lyrics: '歌词语义',
    exact: '精确匹配',
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
    onSearch(text)
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
            {/* Icon — absolutely positioned, never overlaps text */}
            <div style={{
              position: 'absolute',
              left: '1.125rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: isLoading ? 'var(--accent-pink)' : 'var(--text-muted)',
              pointerEvents: 'none',
              display: 'flex',
              alignItems: 'center',
            }}>
              {isLoading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Search size={20} />
              )}
            </div>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="描述你想要的音乐氛围..."
              className="search-input-with-icon"
              style={{
                flex: 1,
                paddingTop: '1rem',
                paddingBottom: '1rem',
                paddingRight: '1rem',
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
              {isLoading ? '解析中...' : '搜索'}
            </button>
          </div>
        </div>
      </form>

      {/* Intent Indicator */}
      {isLoading && (
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--accent-pink)' }} className="animate-pulse">
          <Sparkles size={14} />
          <span>LLM 正在解析你的意图...</span>
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
