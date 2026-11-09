import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, UserX, Clock, Inbox, Users } from 'lucide-react'
import { api } from '../api'
import { Alerta, Badge, Cargando, Encabezado, Kpi, useCarga, fecha } from '../components/ui'

const PRINCIPIOS = [
  ['Consentimiento informado', 'El candidato acepta un aviso de privacidad versionado antes de postular. Guardamos fecha, versión e IP como evidencia.'],
  ['Minimización', 'Solo pedimos lo necesario para evaluar la candidatura. El puntaje interno y el motivo de descarte nunca se muestran al candidato.'],
  ['Retención limitada', 'Cada candidato tiene una fecha «conservar hasta». Al vencer, la purga anonimiza sus datos y borra el archivo del CV.'],
  ['Derechos del titular', 'Desde su portal, el candidato descarga todos sus datos (acceso) o solicita su eliminación (borrado).'],
  ['Trazabilidad sin datos', 'La bitácora guarda un hash del correo, no el correo: demuestra que se cumplió una solicitud sin volver a guardar el dato.'],
  ['Decisión humana', 'El match score es una ayuda: ningún candidato se descarta automáticamente, siempre lo decide una persona.'],
]

export default function Privacidad() {
  const [d, cargando, error, recargar] = useCarga(() => api.get('/privacidad'), [])
  const [msg, setMsg] = useState('')

  const resolver = async (s, aprobar) => {
    const motivo = aprobar ? undefined : window.prompt('Motivo del rechazo (p. ej. obligación legal de conservar):')
    if (!aprobar && !motivo) return
    await api.post(`/privacidad/solicitudes/${s.id}/resolver`, { aprobar, motivo })
    recargar()
  }
  const purgar = async () => {
    const r = await api.post('/privacidad/purgar')
    setMsg(`Purga ejecutada: ${r.anonimizados} candidato(s) anonimizados.`)
    recargar()
  }

  if (cargando && !d) return <Cargando />
  if (error) return <Alerta>{error}</Alerta>
  const pendientes = d.solicitudes.filter((s) => s.estado === 'pendiente')

  return (
    <div className="space-y-6">
      <Encabezado titulo="Privacidad y protección de datos" subtitulo="Un ATS maneja datos personales sensibles: cumplir no es opcional, y es una señal de confianza para los candidatos.">
        <button className="btn-secondary" onClick={purgar}><Clock className="h-4 w-4" />Ejecutar purga de vencidos</button>
      </Encabezado>
      {msg && <Alerta tipo="ok">{msg}</Alerta>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi titulo="Candidatos con datos" valor={d.metricas.candidatos_activos} icono={Users} />
        <Kpi titulo="Anonimizados" valor={d.metricas.anonimizados} icono={UserX} tono="verde" />
        <Kpi titulo="Retención vencida" valor={d.metricas.vencidos} icono={Clock} tono={d.metricas.vencidos ? 'rosa' : 'verde'} />
        <Kpi titulo="Solicitudes pendientes" valor={d.metricas.pendientes} icono={Inbox} tono={d.metricas.pendientes ? 'ambar' : 'verde'} />
      </div>

      <div className="card p-6">
        <h2 className="mb-4 flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck className="h-5 w-5 text-brand-600" />Por qué importa</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {PRINCIPIOS.map(([t, x]) => (
            <div key={t}><p className="text-sm font-medium text-slate-800">{t}</p><p className="mt-1 text-sm text-slate-500">{x}</p></div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="border-b border-slate-100 px-5 py-3 font-semibold text-slate-900">Solicitudes de titulares</h2>
          <div className="divide-y divide-slate-100">
            {!d.solicitudes.length && <p className="p-5 text-sm text-slate-500">Sin solicitudes.</p>}
            {[...pendientes, ...d.solicitudes.filter((s) => s.estado !== 'pendiente')].map((s) => (
              <div key={s.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-800">
                    {s.candidato_id ? <Link to={`/candidatos/${s.candidato_id}`} className="hover:text-brand-700">{s.candidato}</Link> : <span className="font-mono text-xs">{s.email_hash}</span>}
                  </p>
                  <p className="text-xs text-slate-500">{s.tipo} · {fecha(s.solicitada_en)}{s.motivo && ` · ${s.motivo}`}</p>
                </div>
                {s.estado === 'pendiente' ? (
                  <div className="flex gap-1.5">
                    <button className="btn-danger px-2.5 py-1 text-xs" onClick={() => resolver(s, true)}>Anonimizar</button>
                    <button className="btn-secondary px-2.5 py-1 text-xs" onClick={() => resolver(s, false)}>Rechazar</button>
                  </div>
                ) : <Badge tono={s.estado === 'completada' ? 'verde' : 'gris'}>{s.estado}</Badge>}
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="border-b border-slate-100 px-5 py-3 font-semibold text-slate-900">Próximos a vencer</h2>
          <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto">
            {d.por_vencer.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
                <Link to={`/candidatos/${c.id}`} className="text-slate-700 hover:text-brand-700">{c.nombre}</Link>
                <Badge tono={c.vencido ? 'rojo' : 'gris'}>{c.vencido ? 'vencido' : 'hasta'} {fecha(c.retener_hasta)}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="border-b border-slate-100 px-5 py-3 font-semibold text-slate-900">Bitácora de privacidad</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr><th className="px-5 py-2">Fecha</th><th className="px-5 py-2">Acción</th><th className="px-5 py-2">Hash del correo</th><th className="px-5 py-2">Detalle</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {d.bitacora.map((b) => (
                <tr key={b.id}>
                  <td className="whitespace-nowrap px-5 py-2 text-slate-500">{fecha(b.creado_en, true)}</td>
                  <td className="px-5 py-2"><Badge>{b.accion}</Badge></td>
                  <td className="px-5 py-2 font-mono text-xs text-slate-500">{b.email_hash}</td>
                  <td className="px-5 py-2 text-xs text-slate-500">{b.detalle && Object.entries(b.detalle).map(([k, v]) => `${k}: ${v}`).join(' · ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
