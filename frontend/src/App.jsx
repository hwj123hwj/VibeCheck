import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import SongDetailPage from './pages/SongDetailPage'
import { SearchProvider } from './context/SearchContext'
import { PlayerProvider } from './context/PlayerContext'

function App() {
  return (
    <PlayerProvider>
      <SearchProvider>
        <div className="noise-overlay">
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/song/:id" element={<SongDetailPage />} />
            </Route>
          </Routes>
        </div>
      </SearchProvider>
    </PlayerProvider>
  )
}

export default App
