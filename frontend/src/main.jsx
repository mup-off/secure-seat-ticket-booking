import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
// Fonts are bundled with the app (same origin), so the strict CSP still holds.
import '@fontsource/big-shoulders-display/700';
import '@fontsource/big-shoulders-display/800';
import '@fontsource/big-shoulders-display/900';
import '@fontsource/figtree/400';
import '@fontsource/figtree/500';
import '@fontsource/figtree/600';
import '@fontsource/figtree/700';
import '@fontsource/figtree/800';
import '@fontsource/jetbrains-mono/400';
import '@fontsource/jetbrains-mono/500';
import App from './App.jsx';
import { AuthProvider } from './auth.jsx';
import { ToastProvider } from './toast.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
);
