import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import './styles/main.css'
import Teachers from './components/add/Teachers';
import { Background } from './components/Background';

function App() {

  return (
    <BrowserRouter>
      <div className='global-bg-pattern' />
      <Routes>
        <Route path="/add/teachers" element={<Teachers />} />
        <Route path="/" element={<h1>xD</h1>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
