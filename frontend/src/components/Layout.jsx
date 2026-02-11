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
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
      {/* ── Header ── */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        width: '100%',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(255, 252, 245, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
      }}>
        <div className="page-container" style={{ height: '4rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '2rem' }}>
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none', flexShrink: 0 }}>
            <div style={{
              width: '2rem', height: '2rem', borderRadius: 'var(--radius-md)',
              background: 'var(--accent-pink)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(255, 139, 167, 0.3)',
              transition: 'transform 0.3s',
            }}>
              <Music size={16} color="white" />
            </div>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}>
              Vibe<span style={{ color: 'var(--accent-pink)' }}>Check</span>
            </span>
          </Link>

          {/* Quick Search (hidden on search page) */}
          {location.pathname !== '/search' && (
            <form onSubmit={handleQuickSearch} className="hidden md:block" style={{ flex: 1, maxWidth: '24rem' }}>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{
                  position: 'absolute',
                  left: '0.875rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                  pointerEvents: 'none',
                }} />
                <input
                  type="text"
                  value={quickSearch}
                  onChange={(e) => setQuickSearch(e.target.value)}
                  placeholder="搜索氛围、歌词..."
                  className="search-input-header"
                  style={{
                    width: '100%',
                    paddingTop: '0.5rem',
                    paddingBottom: '0.5rem',
                    paddingRight: '1rem',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid transparent',
                    fontSize: '0.875rem',
                    color: 'var(--text-primary)',
                    outline: 'none',
                    transition: 'all 0.3s',
                  }}
                  onFocus={(e) => {
                    e.target.style.background = 'var(--bg-card)'
                    e.target.style.borderColor = 'rgba(255, 139, 167, 0.3)'
                    e.target.style.boxShadow = '0 0 0 4px rgba(255, 139, 167, 0.08)'
                  }}
                  onBlur={(e) => {
                    e.target.style.background = 'var(--bg-secondary)'
                    e.target.style.borderColor = 'transparent'
                    e.target.style.boxShadow = 'none'
                  }}
                />
              </div>
            </form>
          )}

          {/* Nav */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', flexShrink: 0 }}>
            <NavLink to="/" icon={Home} label="发现" active={location.pathname === '/'} />
            <NavLink to="/search" icon={Search} label="搜索" active={location.pathname === '/search'} />
          </nav>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main style={{ flex: 1, width: '100%' }}>
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '2rem 0',
        marginTop: '3rem',
        background: 'rgba(245, 241, 232, 0.4)',
        width: '100%',
      }}>
        <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-pink)', opacity: 0.5, display: 'inline-block' }} />
            VibeCheck · 懂你的情绪，更懂你的歌
          </p>
          <p style={{ opacity: 0.6 }}>毕业设计 Project © 2026</p>
        </div>
      </footer>
    </div>
  )
}

function NavLink({ to, icon: Icon, label, active }) {
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: '0.5rem 1rem',
        borderRadius: 'var(--radius-full)',
        fontSize: '0.875rem',
        fontWeight: 500,
        textDecoration: 'none',
        transition: 'all 0.3s',
        color: active ? 'var(--accent-pink)' : 'var(--text-secondary)',
        background: active ? 'var(--accent-pink-light)' : 'transparent',
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.color = 'var(--text-primary)'
          e.currentTarget.style.background = 'var(--bg-secondary)'
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.color = 'var(--text-secondary)'
          e.currentTarget.style.background = 'transparent'
        }
      }}
    >
      <Icon size={16} />
      <span>{label}</span>
    </Link>
  )
}


