import { createContext, useContext, useEffect, useState } from 'react'
import { api, sesion } from './api'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(!!sesion.token)

  useEffect(() => {
    if (!sesion.token) return
    api.get('/auth/yo').then(setUsuario).catch(() => sesion.cerrar()).finally(() => setCargando(false))
  }, [])

  const login = async (email, password) => {
    const r = await api.post('/auth/login', { email, password }, { publico: true })
    sesion.guardar(r.token)
    setUsuario(r.usuario)
    return r.usuario
  }
  const logout = () => { sesion.cerrar(); setUsuario(null) }
  const puede = (...roles) => usuario && roles.includes(usuario.rol)

  return <Ctx.Provider value={{ usuario, cargando, login, logout, puede }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
