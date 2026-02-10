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
    <div className="w-full max-w-2xl mx-auto">
      {/* Search Bar */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative group">
          {/* Glow border on focus */}
          <div className="absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-[var(--accent-pink)] to-[var(--accent-blue)] opacity-0 group-focus-within:opacity-30 blur transition-opacity duration-300" />

          <div className="relative flex items-center bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl overflow-hidden group-focus-within:border-[var(--accent-pink)]/40 transition-colors">
            <div className="pl-5 text-[var(--text-muted)]">
              {isLoading ? (
                <Loader2 size={20} className="animate-spin text-[var(--accent-pink)]" />
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
              className="flex-1 px-4 py-4 bg-transparent text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none text-base"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="mr-2 px-5 py-2 rounded-xl bg-[var(--accent-pink)] hover:bg-[var(--accent-pink-dim)] disabled:opacity-30 text-white text-sm font-medium transition-all"
            >
              {isLoading ? '解析中...' : '搜索'}
            </button>
          </div>
        </div>
      </form>

      {/* Intent Indicator */}
      {isLoading && (
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-[var(--accent-pink)] animate-pulse">
          <Sparkles size={14} />
          <span>LLM 正在解析你的意图...</span>
        </div>
      )}

      {intentType && !isLoading && (
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-[var(--text-secondary)]">
          <Sparkles size={14} className="text-[var(--accent-pink)]" />
          <span>
            识别模式：
            <span className="text-[var(--accent-pink)] font-medium ml-1">
              {intentLabels[intentType] || intentType}
            </span>
          </span>
        </div>
      )}

      {/* Example Prompts */}
      {!intentType && !isLoading && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {examples.map((text, i) => (
            <button
              key={i}
              onClick={() => handleExample(text)}
              className="px-3 py-1.5 rounded-full text-xs bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--accent-pink)] hover:border-[var(--accent-pink)]/30 transition-colors"
            >
              {text}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
