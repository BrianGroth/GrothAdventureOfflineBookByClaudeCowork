import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './styles/theme.css'

// HashRouter (#/page/5) instead of BrowserRouter: hash routing needs no
// server-side URL rewriting, so the same build works from file:// (USB copy).
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
