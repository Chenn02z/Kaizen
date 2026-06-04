import {
  init as initSDK,
  isTMA,
  miniApp,
  themeParams,
  viewport,
} from '@telegram-apps/sdk-react'

// Initialise the Telegram SDK. Returns false (and does nothing) outside of
// Telegram so the app still renders in a plain browser during development.
export function initTelegram(): boolean {
  if (!isTMA()) return false

  initSDK()

  if (miniApp.mountSync.isAvailable()) {
    miniApp.mountSync()
    miniApp.bindCssVars()
  }
  if (themeParams.mountSync.isAvailable()) {
    themeParams.mountSync()
    themeParams.bindCssVars()
  }
  if (viewport.mount.isAvailable()) {
    viewport
      .mount()
      .then(() => viewport.bindCssVars())
      .catch(() => {})
  }
  if (miniApp.ready.isAvailable()) miniApp.ready()

  return true
}
