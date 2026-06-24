import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ScreenerPage from './pages/ScreenerPage'
import ScreenerDetailPage from './pages/ScreenerDetailPage'
import TodayPage from './pages/TodayPage'
import BacktestPage from './pages/BacktestPage'
import ComparePage from './pages/ComparePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/today" replace />} />
        <Route path="/today" element={<TodayPage />} />
        <Route path="/screeners" element={<ScreenerPage />} />
        <Route path="/screeners/:id" element={<ScreenerDetailPage />} />
        <Route path="/backtest" element={<BacktestPage />} />
        <Route path="/compare" element={<ComparePage />} />
        {/* Hiển thị tạm TodayPage cho các link chưa có nội dung để không bị lỗi trắng trang */}
        <Route path="*" element={<TodayPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
