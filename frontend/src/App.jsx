import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import SongDetailPage from './pages/SongDetailPage'

function App() {
  return (
    <div className="noise-overlay">
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/song/:id" element={<SongDetailPage />} />
        </Route>
      </Routes>
    </div>
  )
}

export default App
