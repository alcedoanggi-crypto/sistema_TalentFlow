import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, MapPin, Users, Briefcase, Pencil } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Badge, Cargando, Encabezado, Vacio, useCarga, MODALIDAD, dinero, hace, cx } from '../components/ui'

const ESTADOS = { publicada: 'verde', borrador: 'ambar', cerrada: 'gris' }

export default function Vacantes() {
  const { puede } = useAuth()
  const [filtro, setFiltro] = useState('')
  const [vacantes, cargando] = useCarga(() => api.get(`/vacantes${filtro ? `?estado=${filtro}` : ''}`), [filtro])

  return (
    <div>
      <Encabezado titulo="Vacantes" subtitulo="Publica posiciones y gestiona su pipeline de selección.">
        {puede('admin', 'reclutador') && <Link to="/vacantes/nueva" className="btn-primary"><Plus className="h-4 w-4" />Nueva vacante</Link>}
      </Encabezado>
      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-sm w-fit">
        {[['', 'Todas'], ['publicada', 'Publicadas'], ['borrador', 'Borradores'], ['cerrada', 'Cerradas']].map(([v, t]) => (
          <button key={v} onClick={() => setFiltro(v)} className={cx('rounded-md px-3 py-1.5', filtro === v ? 'bg-white font-medium shadow-sm' : 'text-slate-600')}>{t}</button>
        ))}
      </div>
      {cargando ? <Cargando /> : !vacantes.length ? <div className="card"><Vacio icono={Briefcase} titulo="No hay vacantes" /></div> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {vacantes.map((v) => (
            <div key={v.id} className="card group flex flex-col p-5 transition hover:border-brand-200 hover:shadow-md">
              <div className="flex items-start justify-between gap-2">
                <Badge tono={ESTADOS[v.estado]}>{v.estado}</Badge>
                {puede('admin', 'reclutador') && <Link to={`/vacantes/${v.id}/editar`} className="text-slate-400 hover:text-brand-600" title="Editar"><Pencil className="h-4 w-4" /></Link>}
              </div>
              <Link to={`/vacantes/${v.id}`} className="mt-3 text-lg font-semibold text-slate-900 group-hover:text-brand-700">{v.titulo}</Link>
              <p className="mt-1 flex items-center gap-1 text-sm text-slate-500"><MapPin className="h-3.5 w-3.5" />{v.ubicacion} · {MODALIDAD[v.modalidad]}</p>
              {v.salario_min != null && <p className="mt-1 text-sm text-slate-600">{dinero(v.salario_min, v.moneda)} – {dinero(v.salario_max, v.moneda)}</p>}
              <div className="mt-3 flex flex-wrap gap-1">
                {v.habilidades.filter((h) => h.tipo === 'obligatoria').map((h) => <Badge key={h.id} tono="marca">{h.nombre}</Badge>)}
                {v.habilidades.filter((h) => h.tipo === 'deseable').slice(0, 3).map((h) => <Badge key={h.id}>{h.nombre}</Badge>)}
              </div>
              <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-3 mt-4 text-sm">
                <span className="flex items-center gap-1.5 text-slate-600"><Users className="h-4 w-4" />{v.postulaciones} postulaciones · {v.activas} activas</span>
                <span className="text-xs text-slate-400">{v.publicada_en ? hace(v.publicada_en) : 'sin publicar'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
