import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api } from './api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = still loading

  const refresh = useCallback(async () => {
    // Also makes Django set the CSRF cookie.
    const data = await api.get('/auth/csrf');
    setUser(data.user);
    return data.user;
  }, []);

  useEffect(() => {
    refresh().catch(() => setUser(null));
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.post('/auth/logout');
    await refresh();
  }, [refresh]);

  return <AuthContext.Provider value={{ user, setUser, refresh, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
