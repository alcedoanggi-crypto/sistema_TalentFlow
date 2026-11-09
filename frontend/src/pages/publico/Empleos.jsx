import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { MapPin, Search, Briefcase, Globe } from 'lucide-react'
import { api } from '../../api'
import { Badge, Cargando, Vacio, useCarga, MODALIDAD, dinero, hace } from '../../components/ui'

export function MarcoPublico({ empresa, children }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-4 py-4">
          <div className="grid h-9 w-9 place-items-center rounded-lg font-bold text-white" style={{ background: empresa?.color || '#4f46e5' }}>{empresa?.nombre?.[0] || 'T'}</div>
          <Link to={empresa ? `/empleos/${empresa.slug}` : '#'} className="font-semibold text-slate-900">{empresa?.nombre || 'TalentFlow'}</Link>
          {empresa?.sitio_web && <a href={empresa.sitio_web} target="_blank" rel="noreferrer" className="ml-auto flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><Globe className="h-4 w-4" />Sitio web</a>}
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
      <footer className="pb-8 text-center text-xs text-slate-400">Impulsado por TalentFlow</footer>
    </div>
  )
}

export default function Empleos() {
  const { slug } = useParams()
  const [d, cargando, error] = useCarga(() => api.get(`/publico/empresas/${slug}`, { publico: true }), [slug])
  const [q, setQ] = useState('')
  const [modalidad, setModalidad] = useState('')

  if (cargando) return <Cargando />
  if (error) return <MarcoPublico><Vacio icono={Briefcase} titulo="Empresa no encontrada" /></MarcoPublico>

  const lista = d.vacantes.filter((v) => (!modalidad || v.modalidad === modalidad)
    && (!q || `${v.titulo} ${v.departamento} ${v.habilidades.map((h) => h.nombre).join(' ')}`.toLowerCase().includes(q.toLowerCase())))

  return (
    <MarcoPublico empresa={d.empresa}>
      <section className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Trabaja en {d.empresa.nombre}</h1>
        {d.empresa.descripcion && <p className="mt-2 max-w-2xl text-slate-600">{d.empresa.descripcion}</p>}
      </section>
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-60 flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input pl-9" placeholder="Buscar por puesto o habilidad" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="input w-auto" value={modalidad} onChange={(e) => setModalidad(e.target.value)}>
          <option value="">Todas las modalidades</option>
          {Object.entries(MODALIDAD).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <p className="mb-3 text-sm text-slate-500">{lista.length} vacante{lista.length !== 1 && 's'} abierta{lista.length !== 1 && 's'}</p>
      {!lista.length ? <div className="card"><Vacio icono={Briefcase} titulo="No hay vacantes con esos filtros" /></div> : (
        <div className="space-y-3">
          {lista.map((v) => (
            <Link key={v.id} to={`/empleos/${slug}/${v.slug}`} className="card block p-5 transition hover:border-brand-200 hover:shadow-md">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{v.titulo}</h2>
                  <p className="mt-0.5 flex items-center gap-1 text-sm text-slate-500"><MapPin className="h-3.5 w-3.5" />{v.ubicacion} · {v.departamento}</p>
                </div>
                <Badge tono="marca">{MODALIDAD[v.modalidad]}</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">{v.habilidades.filter((h) => h.tipo === 'obligatoria').map((h) => <Badge key={h.id}>{h.nombre}</Badge>)}</div>
              <div className="mt-3 flex justify-between text-sm">
                <span className="font-medium text-slate-700">{v.salario_min != null ? `${dinero(v.salario_min, v.moneda)} – ${dinero(v.salario_max, v.moneda)}` : ''}</span>
                <span className="text-xs text-slate-400">Publicada {hace(v.publicada_en)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </MarcoPublico>
  )
}
