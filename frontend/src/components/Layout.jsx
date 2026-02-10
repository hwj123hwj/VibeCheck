import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { Search, Home, Music } from 'lucide-react'
import { useState } from 'react'

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [quickSearch, setQuickSearch] = useState('')

  const handleQuickSearch = (e) => {
    e.preventDefault()
    if (quickSearch.trim()) {
      navigate(`/search?q=${encodeURIComponent(quickSearch.trim())}`)
      setQuickSearch('')
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 shrink-0 group">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-pink)] flex items-center justify-center group-hover:glow-pink transition-shadow">
              <Music size={18} className="text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              Vibe<span className="text-[var(--accent-pink)]">Check</span>
            </span>
          </Link>

          {/* Quick Search (hidden on search page) */}
          {location.pathname !== '/search' && (
            <form onSubmit={handleQuickSearch} className="flex-1 max-w-md">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  type="text"
                  value={quickSearch}
                  onChange={(e) => setQuickSearch(e.target.value)}
                  placeholder="搜索氛围、歌词、歌名..."
                  className="w-full pl-9 pr-4 py-2 rounded-full bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-pink)]/50 transition-colors"
                />
              </div>
            </form>
          )}

          {/* Nav */}
          <nav className="flex items-center gap-1 shrink-0">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                location.pathname === '/'
                  ? 'text-[var(--accent-pink)] bg-[var(--accent-pink)]/10'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Home size={16} className="inline mr-1 -mt-0.5" />
              发现
            </Link>
            <Link
              to="/search"
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                location.pathname === '/search'
                  ? 'text-[var(--accent-pink)] bg-[var(--accent-pink)]/10'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Search size={16} className="inline mr-1 -mt-0.5" />
              搜索
            </Link>
          </nav>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-[var(--border-subtle)] py-6">
        <div className="max-w-7xl mx-auto px-6 text-center text-xs text-[var(--text-muted)]">
          <p>VibeCheck · 基于 LLM 语义评语的混合音乐推荐系统 · 毕业设计</p>
        </div>
      </footer>
    </div>
  )
}
