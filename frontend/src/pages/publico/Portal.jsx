import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Check, CalendarDays, FileCode2, ShieldCheck, Download, Trash2, UserCircle } from 'lucide-react'
import { api } from '../../api'
import { Alerta, Badge, Cargando, Modal, Vacio, useCarga, fecha, cx, MODALIDAD } from '../../components/ui'
import { MarcoPublico } from './Empleos'
import { TIPOS_ENTREVISTA } from '../../components/acciones'

export default function Portal() {
  const { token } = useParams()
  const [d, cargando, error] = useCarga(() => api.get(`/publico/portal/${token}`, { publico: true }), [token])
  const [borrar, setBorrar] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [msg, setMsg] = useState('')

  if (cargando) return <Cargando />
  if (error) return <MarcoPublico><Vacio icono={UserCircle} titulo="Enlace inválido" texto="Este enlace no existe o tus datos ya fueron eliminados." /></MarcoPublico>

  const solicitar = async (tipo) => {
    const r = await api.post(`/publico/portal/${token}/privacidad`, { tipo, motivo: motivo || null }, { publico: true })
    setMsg(r.mensaje)
    if (tipo === 'acceso') {
      const url = URL.createObjectURL(new Blob([JSON.stringify(r.datos, null, 2)], { type: 'application/json' }))
      Object.assign(document.createElement('a'), { href: url, download: 'mis-datos-talentflow.json' }).click()
      URL.revokeObjectURL(url)
    }
    setBorrar(false)
  }

  return (
    <MarcoPublico>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Hola, {d.nombre.split(' ')[0]}</h1>
      <p className="mt-1 text-slate-500">Aquí puedes seguir el estado de tus postulaciones.</p>
      {msg && <div className="mt-4"><Alerta tipo="ok">{msg}</Alerta></div>}

      <div className="mt-6 space-y-4">
        {d.postulaciones.map((p) => {
          const finalizado = p.etapa.codigo === 'descartado'
          return (
            <div key={p.id} className="card p-6">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{p.vacante}</h2>
                  <p className="text-sm text-slate-500">{p.empresa} · {MODALIDAD[p.modalidad]} · postulaste el {fecha(p.fecha)}</p>
                </div>
                <Badge tono={finalizado ? 'gris' : p.etapa.codigo === 'contratado' ? 'verde' : 'marca'}>{p.etapa.nombre}</Badge>
              </div>

              {/* Línea de progreso */}
              {finalizado ? (
                <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">El proceso para esta vacante finalizó. Gracias por tu interés: conservaremos tu perfil para futuras oportunidades durante el periodo indicado abajo.</p>
              ) : (
                <ol className="mt-6 flex items-center">
                  {d.etapas.map((e, i) => {
                    const hecho = e.orden < p.etapa.orden
                    const actual = e.orden === p.etapa.orden
                    return (
                      <li key={e.codigo} className={cx('flex items-center', i < d.etapas.length - 1 && 'flex-1')}>
                        <div className="flex flex-col items-center">
                          <div className={cx('grid h-7 w-7 place-items-center rounded-full text-xs font-semibold',
                            hecho ? 'bg-brand-600 text-white' : actual ? 'bg-brand-600 text-white ring-4 ring-brand-100' : 'bg-slate-200 text-slate-500')}>
                            {hecho ? <Check className="h-4 w-4" /> : i + 1}
                          </div>
                          <span className={cx('mt-1.5 hidden w-20 text-center text-[11px] sm:block', actual ? 'font-semibold text-brand-700' : 'text-slate-500')}>{e.nombre}</span>
                        </div>
                        {i < d.etapas.length - 1 && <div className={cx('mx-1 h-0.5 flex-1 sm:-mt-5', hecho ? 'bg-brand-600' : 'bg-slate-200')} />}
                      </li>
                    )
                  })}
                </ol>
              )}

              {(p.entrevistas.length > 0 || p.pruebas.length > 0) && (
                <div className="mt-5 space-y-2 border-t border-slate-100 pt-4">
                  {p.entrevistas.map((e, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-slate-700">
                      <CalendarDays className="h-4 w-4 text-brand-600" />
                      Entrevista {TIPOS_ENTREVISTA[e.tipo]?.toLowerCase()} · <b>{fecha(e.inicio, true)}</b> · {e.duracion_min} min
                      {e.lugar?.startsWith('http') && <a href={e.lugar} target="_blank" rel="noreferrer" className="text-brand-600 underline">enlace</a>}
                    </div>
                  ))}
                  {p.pruebas.map((t, i) => (
                    <div key={i} className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                      <FileCode2 className="h-4 w-4 text-brand-600" />{t.titulo}
                      {t.completada ? <Badge tono="verde">Completada</Badge> : t.vencida ? <Badge>Vencida</Badge>
                        : <Link to={t.enlace} className="btn-primary px-2.5 py-1 text-xs">Resolver (vence {fecha(t.expira_en)})</Link>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="card mt-8 p-6">
        <h2 className="flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck className="h-5 w-5 text-brand-600" />Tus datos personales</h2>
        <p className="mt-1 text-sm text-slate-600">Conservamos tu información hasta el <b>{fecha(d.retener_hasta)}</b>; después se anonimiza automáticamente. Puedes ejercer tus derechos en cualquier momento.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={() => solicitar('acceso')}><Download className="h-4 w-4" />Descargar mis datos</button>
          <button className="btn-ghost text-rose-600" onClick={() => setBorrar(true)}><Trash2 className="h-4 w-4" />Solicitar borrado</button>
        </div>
      </div>

      <Modal abierto={borrar} onCerrar={() => setBorrar(false)} titulo="Solicitar borrado de mis datos">
        <p className="text-sm text-slate-600">Eliminaremos tu CV y anonimizaremos tus datos en un máximo de 10 días hábiles. Tus postulaciones activas se cerrarán.</p>
        <textarea className="input mt-3" rows={2} placeholder="Motivo (opcional)" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setBorrar(false)}>Cancelar</button>
          <button className="btn-danger" onClick={() => solicitar('borrado')}>Solicitar borrado</button>
        </div>
      </Modal>
    </MarcoPublico>
  )
}
