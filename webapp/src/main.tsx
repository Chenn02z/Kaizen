import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@telegram-apps/telegram-ui/dist/styles.css'
import './index.css'
import App from './App.tsx'
import { initTelegram } from './init.ts'

initTelegram()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
