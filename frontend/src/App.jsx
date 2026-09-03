import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import ScreenerPage from './pages/ScreenerPage'
import ScreenerDetailPage from './pages/ScreenerDetailPage'
import TodayPage from './pages/TodayPage'
import ComparePage from './pages/ComparePage'
import TradingViewPage from './pages/TradingViewPage'
import PortfolioPage from './pages/PortfolioPage'
import WatchlistPage from './pages/WatchlistPage'
import StockDetailPage from './pages/StockDetailPage'

import { AgentProvider } from './contexts/AgentContext'

function App() {
  return (
    <AuthProvider>
      <AgentProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/today" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/today" element={<TodayPage />} />
            <Route path="/screeners" element={<ScreenerPage />} />
            <Route path="/screeners/:id" element={<ScreenerDetailPage />} />
            <Route path="/compare" element={<ProtectedRoute><ComparePage /></ProtectedRoute>} />
            <Route path="/chart" element={<TradingViewPage />} />
            <Route path="/portfolio" element={<ProtectedRoute><PortfolioPage /></ProtectedRoute>} />
            <Route path="/watchlist" element={<ProtectedRoute><WatchlistPage /></ProtectedRoute>} />
            <Route path="/stock/:ticker" element={<StockDetailPage />} />
            {/* Fallback */}
            <Route path="*" element={<TodayPage />} />
          </Routes>
        </BrowserRouter>
      </AgentProvider>
    </AuthProvider>
  )
}

export default App
