import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { PAGE_TITLE } from './brand'
// Theme layer: loads after App.css. Remove this line for the plain theme.
import './theme-retro.css'
// Shared pieces (toast, skeletons, the timer dial, the saved screen).
import './ui.css'
import './dogs.css'
// Motion layer: loads last. Remove this line and nothing moves; everything still works.
import './motion.css'

document.title = PAGE_TITLE

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
