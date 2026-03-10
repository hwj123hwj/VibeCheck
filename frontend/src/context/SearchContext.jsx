import { createContext, useContext, useRef } from 'react'

const SearchContext = createContext(null)

/**
 * 搜索结果缓存 — 用 useRef 存储，不触发任何 re-render
 * 结构：{ query: string, results: [], intentType: string|null, hasSearched: bool }
 */
export function SearchProvider({ children }) {
  const cache = useRef({ query: '', results: [], intentType: null, hasSearched: false })
  return (
    <SearchContext.Provider value={cache}>
      {children}
    </SearchContext.Provider>
  )
}

export function useSearchCache() {
  return useContext(SearchContext)
}
