import { createContext, useContext, useEffect, useState } from 'react'
import { api, getStoredUser, getToken, setSession } from './api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser())
  const [meta, setMeta] = useState({ categorias: [], locais: [], vantagens: [] })

  useEffect(() => {
    api('/api/meta').then(setMeta).catch(() => {})
    if (getToken()) api('/api/auth/me').then(setUser).catch(() => { setSession(null); setUser(null) })
  }, [])

  const entrar = (data) => { setSession(data.access_token, data.user); setUser(data.user) }
  const sair = () => { setSession(null); setUser(null) }
  const nomeCategoria = (id) => meta.categorias.find((c) => c.id === id)?.nome || id

  return <AuthCtx.Provider value={{ user, entrar, sair, meta, nomeCategoria }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)

export const homeDe = (role) => ({ candidato: '/inicio', empresa: '/empresa', parceiro: '/parceiro', admin: '/admin' }[role] || '/')
