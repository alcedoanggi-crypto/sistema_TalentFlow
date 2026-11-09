import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Users } from 'lucide-react'
import { api } from '../api'
import { Badge, Cargando, Encabezado, Vacio, useCarga } from '../components/ui'

export default function Candidatos() {
  const [texto, setTexto] = useState('')
  const [habilidad, setHabilidad] = useState('')
  const [filtro, setFiltro] = useState({ q: '', h: '' })
  const params = new URLSearchParams()
  if (filtro.q) params.set('q', filtro.q)
  filtro.h.split(',').map((s) => s.trim()).filter(Boolean).forEach((h) => params.append('habilidad', h))
  const [lista, cargando] = useCarga(() => api.get(`/candidatos?${params}`), [filtro.q, filtro.h])

  return (
    <div>
      <Encabezado titulo="Candidatos" subtitulo="Búsqueda full-text sobre el contenido de los CV (PostgreSQL + índice GIN)." />
      <form className="card mb-4 grid gap-3 p-4 md:grid-cols-[1fr_16rem_auto]" onSubmit={(e) => { e.preventDefault(); setFiltro({ q: texto, h: habilidad }) }}>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input pl-9" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder='Ej. "microservicios" python -java' />
        </div>
        <input className="input" value={habilidad} onChange={(e) => setHabilidad(e.target.value)} placeholder="Habilidades: JS, Postgres…" title="Se resuelven sinónimos: JS = JavaScript" />
        <button className="btn-primary">Buscar</button>
      </form>
      {cargando ? <Cargando /> : !lista.length ? <div className="card"><Vacio icono={Users} titulo="Sin resultados" texto="Prueba con otras palabras o quita filtros." /></div> : (
        <div className="card divide-y divide-slate-100">
          {lista.map((c) => (
            <Link key={c.id} to={`/candidatos/${c.id}`} className="block p-4 transition hover:bg-slate-50">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-medium text-slate-900">{c.nombre}</span>
                <span className="text-sm text-slate-500">{c.email}</span>
                <span className="text-sm text-slate-500">· {c.experiencia_anios} años</span>
                {c.relevancia != null && <Badge tono="marca" className="ml-auto">relevancia {c.relevancia}</Badge>}
              </div>
              {c.fragmento && <p className="mt-1.5 text-sm text-slate-600" dangerouslySetInnerHTML={{ __html: `…${limpiar(c.fragmento)}…` }} />}
              <div className="mt-2 flex flex-wrap gap-1">{c.habilidades.slice(0, 10).map((h) => <Badge key={h}>{h}</Badge>)}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

/** ts_headline devuelve texto del CV con <mark>: se escapa todo y solo se restaura <mark>. */
function limpiar(html) {
  const esc = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc.replace(/&lt;mark&gt;/g, '<mark>').replace(/&lt;\/mark&gt;/g, '</mark>')
}
