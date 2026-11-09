import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, Download, Video } from 'lucide-react'
import { api, descargar } from '../api'
import { useAuth } from '../auth'
import { Badge, Cargando, Encabezado, Vacio, useCarga, cx } from '../components/ui'
import { Evaluar, TIPOS_ENTREVISTA } from '../components/acciones'

const ESTADO = { programada: 'azul', realizada: 'verde', cancelada: 'gris' }

export default function Entrevistas() {
  const { usuario, puede } = useAuth()
  const [mias, setMias] = useState(false)
  const [vista, setVista] = useState('proximas')
  const [lista, cargando, , recargar] = useCarga(() => api.get(`/entrevistas?mias=${mias}`), [mias])
  const [evaluando, setEvaluando] = useState(null)

  const ahora = Date.now()
  const filtradas = (lista || []).filter((e) => vista === 'proximas'
    ? new Date(e.inicio) >= ahora - 3600e3 && e.estado === 'programada'
    : new Date(e.inicio) < ahora || e.estado !== 'programada')
  if (vista === 'pasadas') filtradas.reverse()

  // Agrupa por día
  const dias = {}
  filtradas.forEach((e) => {
    const k = new Date(e.inicio).toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })
    ;(dias[k] ||= []).push(e)
  })

  const cancelar = async (e) => { await api.patch(`/entrevistas/${e.id}`, { estado: 'cancelada' }); recargar() }

  return (
    <div>
      <Encabezado titulo="Agenda de entrevistas" subtitulo="Cada invitación incluye un archivo .ics compatible con Google Calendar, Outlook y Apple Calendar.">
        {usuario.rol !== 'entrevistador' && (
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" className="accent-brand-600" checked={mias} onChange={(e) => setMias(e.target.checked)} />Solo las mías</label>
        )}
      </Encabezado>
      <div className="mb-4 flex w-fit gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        {[['proximas', 'Próximas'], ['pasadas', 'Pasadas / por evaluar']].map(([k, t]) => (
          <button key={k} onClick={() => setVista(k)} className={cx('rounded-md px-3 py-1.5', vista === k ? 'bg-white font-medium shadow-sm' : 'text-slate-600')}>{t}</button>
        ))}
      </div>
      {cargando ? <Cargando /> : !filtradas.length ? <div className="card"><Vacio icono={CalendarDays} titulo="Sin entrevistas" texto="Prográmalas desde la ficha de un candidato." /></div> : (
        <div className="space-y-6">
          {Object.entries(dias).map(([dia, es]) => (
            <div key={dia}>
              <h2 className="mb-2 text-sm font-semibold capitalize text-slate-500">{dia}</h2>
              <div className="card divide-y divide-slate-100">
                {es.map((e) => {
                  const evaluada = e.evaluaciones.some((x) => x.evaluador_id === usuario.id)
                  const soyEntrevistador = e.entrevistadores.some((x) => x.id === usuario.id) || puede('admin')
                  return (
                    <div key={e.id} className="flex flex-wrap items-center gap-4 p-4">
                      <div className="w-16 text-center">
                        <p className="text-lg font-semibold tabular-nums text-slate-900">{new Date(e.inicio).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}</p>
                        <p className="text-xs text-slate-400">{e.duracion_min} min</p>
                      </div>
                      <div className="min-w-0 flex-1">
                        <Link to={`/candidatos/${e.candidato_id}`} className="font-medium text-slate-900 hover:text-brand-700">{e.candidato}</Link>
                        <p className="text-sm text-slate-500">{TIPOS_ENTREVISTA[e.tipo]} · {e.vacante}</p>
                        <p className="text-xs text-slate-400">{e.entrevistadores.map((x) => x.nombre).join(', ')}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tono={ESTADO[e.estado]}>{e.estado}</Badge>
                        {e.evaluaciones.length > 0 && <Badge tono="morado">{e.evaluaciones.length} evaluación(es)</Badge>}
                        {e.lugar?.startsWith('http') && e.estado === 'programada' && <a href={e.lugar} target="_blank" rel="noreferrer" className="btn-ghost px-2 py-1" title="Unirse"><Video className="h-4 w-4" /></a>}
                        <button className="btn-ghost px-2 py-1" title="Descargar .ics" onClick={() => descargar(`/entrevistas/${e.id}/ics`, 'entrevista.ics')}><Download className="h-4 w-4" /></button>
                        {soyEntrevistador && e.estado !== 'cancelada' && <button className="btn-secondary px-2.5 py-1 text-xs" onClick={() => setEvaluando(e)}>{evaluada ? 'Editar evaluación' : 'Evaluar'}</button>}
                        {puede('admin', 'reclutador') && e.estado === 'programada' && <button className="btn-ghost px-2 py-1 text-xs text-rose-600" onClick={() => cancelar(e)}>Cancelar</button>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
      {evaluando && <Evaluar entrevista={evaluando} onCerrar={() => setEvaluando(null)} onListo={recargar} />}
    </div>
  )
}
