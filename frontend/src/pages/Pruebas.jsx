import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileCode2, Plus, Trash2, ListChecks, Code2, CheckCircle2, XCircle, Play } from 'lucide-react'
import { api } from '../api'
import { Alerta, Badge, Cargando, Campo, Encabezado, Modal, Vacio, useCarga, fecha, cx } from '../components/ui'

export default function Pruebas() {
  const [lista, cargando, , recargar] = useCarga(() => api.get('/pruebas'), [])
  const [verId, setVerId] = useState(null)
  const [creando, setCreando] = useState(false)

  return (
    <div>
      <Encabezado titulo="Pruebas técnicas" subtitulo="Opción múltiple y ejercicios de código Python calificados automáticamente contra casos de prueba.">
        <button className="btn-primary" onClick={() => setCreando(true)}><Plus className="h-4 w-4" />Nueva prueba</button>
      </Encabezado>
      {cargando ? <Cargando /> : !lista.length ? <div className="card"><Vacio icono={FileCode2} titulo="Aún no hay pruebas" /></div> : (
        <div className="grid gap-4 md:grid-cols-2">
          {lista.map((p) => (
            <button key={p.id} onClick={() => setVerId(p.id)} className="card p-5 text-left transition hover:border-brand-200 hover:shadow-md">
              <p className="font-semibold text-slate-900">{p.titulo}</p>
              {p.descripcion && <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.descripcion}</p>}
              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge><ListChecks className="h-3 w-3" />{p.preguntas.filter((q) => q.tipo === 'opcion_multiple').length} opción múltiple</Badge>
                <Badge><Code2 className="h-3 w-3" />{p.preguntas.filter((q) => q.tipo === 'codigo').length} código</Badge>
                <Badge>{p.tiempo_limite_min} min</Badge>
                <Badge tono="marca">aprueba con {p.puntaje_aprobacion}%</Badge>
              </div>
              <p className="mt-3 border-t border-slate-100 pt-3 text-sm text-slate-600">
                {p.asignadas} enviadas · {p.completadas} completadas{p.promedio != null && <> · promedio <b>{p.promedio}%</b></>}
              </p>
            </button>
          ))}
        </div>
      )}
      {verId && <DetallePrueba id={verId} onCerrar={() => setVerId(null)} />}
      {creando && <NuevaPrueba onCerrar={() => setCreando(false)} onListo={recargar} />}
    </div>
  )
}

function DetallePrueba({ id, onCerrar }) {
  const [p] = useCarga(() => api.get(`/pruebas/${id}`), [id])
  const [abierta, setAbierta] = useState(null)
  return (
    <Modal abierto onCerrar={onCerrar} titulo={p?.titulo || 'Prueba'} ancho="max-w-3xl">
      {!p ? <Cargando /> : (
        <div className="space-y-5">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Resultados ({p.asignaciones.length})</h3>
            <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {!p.asignaciones.length && <p className="p-3 text-sm text-slate-500">Se envía desde la ficha del candidato.</p>}
              {p.asignaciones.map((a) => (
                <div key={a.id}>
                  <button className="flex w-full items-center gap-3 p-3 text-left text-sm hover:bg-slate-50" onClick={() => setAbierta(abierta === a.id ? null : a.id)}>
                    <Link to={`/candidatos/${a.candidato_id}`} onClick={onCerrar} className="font-medium text-slate-800 hover:text-brand-700">{a.candidato}</Link>
                    <span className="text-xs text-slate-400">{a.vacante}</span>
                    <span className="ml-auto tabular-nums">{a.completada_en ? `${a.puntaje} / ${a.puntaje_max}` : <Badge tono="ambar">pendiente</Badge>}</span>
                  </button>
                  {abierta === a.id && a.respuestas.length > 0 && (
                    <div className="space-y-2 bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">Completada {fecha(a.completada_en, true)}</p>
                      {a.respuestas.map((r) => {
                        const q = p.preguntas.find((x) => x.id === r.pregunta_id)
                        const max = q?.puntos || 0
                        return (
                          <div key={r.pregunta_id} className="rounded-md bg-white p-2 text-xs">
                            <div className="flex items-center gap-2">
                              {r.puntos >= max ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-rose-500" />}
                              <span className="flex-1 truncate text-slate-700">{q?.enunciado}</span>
                              <span className="tabular-nums">{r.puntos}/{max}</span>
                            </div>
                            {r.detalle?.casos && <p className="mt-1 pl-6 text-slate-500">{r.detalle.casos.filter((c) => c.ok).length}/{r.detalle.casos.length} casos correctos</p>}
                            {r.detalle?.error && <p className="mt-1 pl-6 text-rose-600">{r.detalle.error}</p>}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Preguntas</h3>
            <ol className="space-y-2">
              {p.preguntas.map((q, i) => (
                <li key={q.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <p className="font-medium text-slate-800">{i + 1}. {q.enunciado} <span className="text-xs font-normal text-slate-400">({q.puntos} pts)</span></p>
                  {q.tipo === 'opcion_multiple' ? (
                    <ul className="mt-1 space-y-0.5 pl-4 text-slate-600">
                      {q.opciones.map((o, j) => <li key={j} className={cx(j === q.respuesta_correcta && 'font-medium text-emerald-700')}>{j === q.respuesta_correcta ? '✓ ' : '· '}{o}</li>)}
                    </ul>
                  ) : <p className="mt-1 text-xs text-slate-500">Función <code>{q.funcion}</code> · {q.casos_prueba?.length} casos de prueba</p>}
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </Modal>
  )
}

const VACIA_OM = () => ({ tipo: 'opcion_multiple', enunciado: '', opciones: ['', ''], respuesta_correcta: 0, puntos: 10 })
const VACIA_COD = () => ({ tipo: 'codigo', enunciado: '', funcion: 'resolver', plantilla_codigo: 'def resolver(x):\n    pass\n', casos: '[[1], 2]\n[[5], 10]', referencia: '', puntos: 20 })

function NuevaPrueba({ onCerrar, onListo }) {
  const [f, setF] = useState({ titulo: '', descripcion: '', tiempo_limite_min: 45, puntaje_aprobacion: 60 })
  const [qs, setQs] = useState([VACIA_OM()])
  const [error, setError] = useState('')
  const [pruebaRef, setPruebaRef] = useState({})

  const setQ = (i, cambios) => setQs(qs.map((q, j) => (j === i ? { ...q, ...cambios } : q)))
  // Cada línea de casos: [argumentos], esperado  → {"entrada": [...], "esperado": ...}
  const parsearCasos = (txt) => txt.split('\n').filter((l) => l.trim()).map((l) => {
    const [entrada, esperado] = JSON.parse(`[${l}]`)
    return { entrada, esperado }
  })

  const probar = async (i) => {
    const q = qs[i]
    try {
      const r = await api.post('/pruebas/probar-codigo', { codigo: q.referencia, funcion: q.funcion, casos: parsearCasos(q.casos) })
      setPruebaRef({ ...pruebaRef, [i]: r.error ? r.error : `${r.casos?.filter((c) => c.ok).length ?? 0}/${r.casos?.length ?? 0} casos OK` })
    } catch (e) { setPruebaRef({ ...pruebaRef, [i]: e.message }) }
  }

  const guardar = async () => {
    setError('')
    try {
      const preguntas = qs.map((q) => q.tipo === 'codigo'
        ? { tipo: 'codigo', enunciado: q.enunciado, funcion: q.funcion, plantilla_codigo: q.plantilla_codigo, casos_prueba: parsearCasos(q.casos), puntos: +q.puntos }
        : { tipo: q.tipo, enunciado: q.enunciado, opciones: q.opciones, respuesta_correcta: +q.respuesta_correcta, puntos: +q.puntos })
      await api.post('/pruebas', { ...f, tiempo_limite_min: +f.tiempo_limite_min, puntaje_aprobacion: +f.puntaje_aprobacion, preguntas })
      onListo(); onCerrar()
    } catch (e) { setError(e instanceof SyntaxError ? 'Casos de prueba con formato inválido. Usa: [argumentos], esperado' : e.message) }
  }

  return (
    <Modal abierto onCerrar={onCerrar} titulo="Nueva prueba técnica" ancho="max-w-3xl">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_8rem_8rem]">
          <Campo label="Título"><input className="input" value={f.titulo} onChange={(e) => setF({ ...f, titulo: e.target.value })} /></Campo>
          <Campo label="Minutos"><input type="number" className="input" value={f.tiempo_limite_min} onChange={(e) => setF({ ...f, tiempo_limite_min: e.target.value })} /></Campo>
          <Campo label="% aprobación"><input type="number" className="input" value={f.puntaje_aprobacion} onChange={(e) => setF({ ...f, puntaje_aprobacion: e.target.value })} /></Campo>
        </div>
        <Campo label="Instrucciones"><textarea className="input" rows={2} value={f.descripcion} onChange={(e) => setF({ ...f, descripcion: e.target.value })} /></Campo>

        {qs.map((q, i) => (
          <div key={i} className="rounded-lg border border-slate-200 p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-700">Pregunta {i + 1}</span>
              <Badge>{q.tipo === 'codigo' ? 'Código' : 'Opción múltiple'}</Badge>
              <input type="number" className="input ml-auto w-20" value={q.puntos} onChange={(e) => setQ(i, { puntos: e.target.value })} title="Puntos" />
              <button className="btn-ghost p-1.5" onClick={() => setQs(qs.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></button>
            </div>
            <textarea className="input mb-2" rows={2} placeholder="Enunciado" value={q.enunciado} onChange={(e) => setQ(i, { enunciado: e.target.value })} />
            {q.tipo === 'opcion_multiple' ? (
              <div className="space-y-1.5">
                {q.opciones.map((o, j) => (
                  <div key={j} className="flex items-center gap-2">
                    <input type="radio" className="accent-emerald-600" checked={+q.respuesta_correcta === j} onChange={() => setQ(i, { respuesta_correcta: j })} title="Correcta" />
                    <input className="input" value={o} placeholder={`Opción ${j + 1}`} onChange={(e) => setQ(i, { opciones: q.opciones.map((x, k) => (k === j ? e.target.value : x)) })} />
                  </div>
                ))}
                <button className="text-xs text-brand-600" onClick={() => setQ(i, { opciones: [...q.opciones, ''] })}>+ opción</button>
              </div>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                <Campo label="Nombre de la función"><input className="input font-mono" value={q.funcion} onChange={(e) => setQ(i, { funcion: e.target.value })} /></Campo>
                <div />
                <Campo label="Plantilla para el candidato"><textarea className="input font-mono text-xs" rows={4} value={q.plantilla_codigo} onChange={(e) => setQ(i, { plantilla_codigo: e.target.value })} /></Campo>
                <Campo label="Casos (una línea: [args], esperado)"><textarea className="input font-mono text-xs" rows={4} value={q.casos} onChange={(e) => setQ(i, { casos: e.target.value })} /></Campo>
                <Campo label="Tu solución de referencia (opcional, para validar casos)" className="md:col-span-2">
                  <textarea className="input font-mono text-xs" rows={3} value={q.referencia} onChange={(e) => setQ(i, { referencia: e.target.value })} />
                </Campo>
                <div className="flex items-center gap-2 md:col-span-2">
                  <button className="btn-secondary px-2.5 py-1 text-xs" disabled={!q.referencia} onClick={() => probar(i)}><Play className="h-3 w-3" />Probar casos</button>
                  {pruebaRef[i] && <span className="text-xs text-slate-600">{pruebaRef[i]}</span>}
                </div>
              </div>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setQs([...qs, VACIA_OM()])}><ListChecks className="h-4 w-4" />Opción múltiple</button>
          <button className="btn-secondary" onClick={() => setQs([...qs, VACIA_COD()])}><Code2 className="h-4 w-4" />Código</button>
        </div>
        <Alerta>{error}</Alerta>
        <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
          <button className="btn-secondary" onClick={onCerrar}>Cancelar</button>
          <button className="btn-primary" disabled={!f.titulo || !qs.length} onClick={guardar}>Guardar prueba</button>
        </div>
      </div>
    </Modal>
  )
}
