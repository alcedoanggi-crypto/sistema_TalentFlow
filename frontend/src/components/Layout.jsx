import { NavLink, Outlet, Link } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, Briefcase, Users, CalendarDays, FileCode2, Mail, Tags, ShieldCheck, Compass, LogOut, Globe, Menu, X,
} from 'lucide-react'
import { useAuth } from '../auth'
import { cx } from './ui'

const NAV = [
  { a: '/', t: 'Dashboard', i: LayoutDashboard, fin: true },
  { a: '/vacantes', t: 'Vacantes', i: Briefcase },
  { a: '/candidatos', t: 'Candidatos', i: Users },
  { a: '/entrevistas', t: 'Entrevistas', i: CalendarDays },
  { a: '/pruebas', t: 'Pruebas técnicas', i: FileCode2, roles: ['admin', 'reclutador'] },
  { a: '/comunicacion', t: 'Comunicación', i: Mail, roles: ['admin', 'reclutador'] },
  { a: '/habilidades', t: 'Habilidades', i: Tags },
  { a: '/privacidad', t: 'Privacidad', i: ShieldCheck, roles: ['admin'] },
]

export default function Layout() {
  const { usuario, logout, puede } = useAuth()
  const [abierto, setAbierto] = useState(false)

  const enlaces = (
    <nav className="flex flex-1 flex-col gap-0.5">
      {NAV.filter((n) => !n.roles || puede(...n.roles)).map((n) => (
        <NavLink key={n.a} to={n.a} end={n.fin} onClick={() => setAbierto(false)}
          className={({ isActive }) => cx('flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
            isActive ? 'bg-white/10 text-white' : 'text-indigo-100/80 hover:bg-white/5 hover:text-white')}>
          <n.i className="h-4 w-4" />{n.t}
        </NavLink>
      ))}
      <div className="mt-4 border-t border-white/10 pt-4">
        <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-indigo-200/60">Uso personal</p>
        <NavLink to="/mi-busqueda" onClick={() => setAbierto(false)}
          className={({ isActive }) => cx('flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
            isActive ? 'bg-white/10 text-white' : 'text-indigo-100/80 hover:bg-white/5 hover:text-white')}>
          <Compass className="h-4 w-4" />Mi búsqueda de empleo
        </NavLink>
      </div>
    </nav>
  )

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className={cx('fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-gradient-to-b from-indigo-950 to-slate-900 p-4 transition-transform lg:translate-x-0',
        abierto ? 'translate-x-0' : '-translate-x-full')}>
        <div className="mb-6 flex items-center justify-between px-2">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-500 font-bold text-white">T</div>
            <div>
              <p className="font-semibold leading-tight text-white">TalentFlow</p>
              <p className="text-[11px] leading-tight text-indigo-200/70">{usuario?.empresa?.nombre}</p>
            </div>
          </Link>
          <button className="text-white lg:hidden" onClick={() => setAbierto(false)}><X className="h-5 w-5" /></button>
        </div>
        {enlaces}
        <a href={`/empleos/${usuario?.empresa?.slug}`} target="_blank" rel="noreferrer"
          className="mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-indigo-200/80 hover:bg-white/5 hover:text-white">
          <Globe className="h-3.5 w-3.5" />Ver página pública de empleos
        </a>
        <div className="flex items-center gap-3 rounded-lg bg-white/5 p-3">
          <div className="grid h-8 w-8 place-items-center rounded-full bg-brand-600 text-xs font-semibold text-white">
            {usuario?.nombre?.split(' ').map((p) => p[0]).slice(0, 2).join('')}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{usuario?.nombre}</p>
            <p className="text-[11px] capitalize text-indigo-200/70">{usuario?.rol}</p>
          </div>
          <button onClick={logout} title="Cerrar sesión" className="text-indigo-200/70 hover:text-white"><LogOut className="h-4 w-4" /></button>
        </div>
      </aside>
      {abierto && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setAbierto(false)} />}
      <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur lg:hidden">
        <button onClick={() => setAbierto(true)}><Menu className="h-5 w-5" /></button>
        <span className="font-semibold">TalentFlow</span>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"><Outlet /></main>
    </div>
  )
}
