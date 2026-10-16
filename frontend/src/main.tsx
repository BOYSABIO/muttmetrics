import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { PAGE_TITLE } from './brand'
// Theme layer: loads after App.css. Remove this line for the plain theme.
import './theme-retro.css'

document.title = PAGE_TITLE

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
