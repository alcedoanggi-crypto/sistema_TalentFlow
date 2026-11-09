import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Timer, CheckCircle2, AlertTriangle, FileCode2 } from 'lucide-react'
import { api } from '../../api'
import { Alerta, Cargando, Vacio, fecha, cx } from '../../components/ui'
import { MarcoPublico } from './Empleos'

export default function PruebaCandidato() {
  const { token } = useParams()
  const [p, setP] = useState(null)
  const [error, setError] = useState('')
  const [resp, setResp] = useState({})
  const [restante, setRestante] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => { api.get(`/publico/pruebas/${token}`, { publico: true }).then(setP).catch((e) => setError(e.message)) }, [token])

  // Cronómetro: el límite real lo controla el servidor; esto solo lo muestra.
  useEffect(() => {
    if (p?.estado !== 'en_curso') return
    const tick = () => setRestante(Math.max(0, Math.floor((new Date(p.limite) - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [p])

  // Borrador local por si se recarga la página
  const clave = `tf_prueba_${token}`
  useEffect(() => { try { const g = localStorage.getItem(clave); if (g) setResp(JSON.parse(g)) } catch { /* sin storage */ } }, [clave])
  useEffect(() => { try { localStorage.setItem(clave, JSON.stringify(resp)) } catch { /* sin storage */ } }, [resp, clave])

  const iniciar = async () => {
    try { setP(await api.post(`/publico/pruebas/${token}/iniciar`, null, { publico: true })) } catch (e) { setError(e.message) }
  }
  const enviar = async () => {
    setEnviando(true)
    try {
      setResultado(await api.post(`/publico/pruebas/${token}/enviar`, { respuestas: resp }, { publico: true }))
      try { localStorage.removeItem(clave) } catch { /* sin storage */ }
    } catch (e) { setError(e.message) } finally { setEnviando(false) }
  }
  useEffect(() => { if (restante === 0 && !resultado && !enviando) enviar() }, [restante]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error && !p) return <MarcoPublico><Vacio icono={FileCode2} titulo="Enlace de prueba inválido" /></MarcoPublico>
  if (!p) return <Cargando />

  const final = resultado || (p.estado === 'completada' ? p : null)
  if (final) return (
    <MarcoPublico>
      <div className="card mx-auto max-w-md p-8 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-500" />
        <h1 className="mt-3 text-xl font-semibold text-slate-900">Prueba enviada</h1>
        <p className="mt-2 text-slate-600">Obtuviste <b>{final.puntaje}</b> de {final.puntaje_max} puntos.</p>
        {resultado?.fuera_de_tiempo && <p className="mt-2 text-sm text-rose-600">Se recibió fuera del tiempo límite.</p>}
        <p className="mt-4 text-sm text-slate-500">El equipo de {p.empresa} revisará tu resultado y te contactará.</p>
      </div>
    </MarcoPublico>
  )
  if (p.estado === 'vencida') return <MarcoPublico><Vacio icono={AlertTriangle} titulo="Esta prueba venció" texto={`El plazo terminó el ${fecha(p.expira_en, true)}.`} /></MarcoPublico>

  if (p.estado === 'pendiente') return (
    <MarcoPublico>
      <div className="card mx-auto max-w-lg p-8">
        <p className="text-sm text-slate-500">{p.empresa} · {p.vacante}</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">{p.titulo}</h1>
        {p.descripcion && <p className="mt-3 text-slate-600">{p.descripcion}</p>}
        <ul className="mt-5 space-y-1 text-sm text-slate-600">
          <li>· {p.num_preguntas} preguntas (opción múltiple y código Python)</li>
          <li>· Tienes <b>{p.tiempo_limite_min} minutos</b> desde que pulses «Comenzar»</li>
          <li>· Disponible hasta el {fecha(p.expira_en, true)}</li>
        </ul>
        <button className="btn-primary mt-6 w-full" onClick={iniciar}>Comenzar</button>
      </div>
    </MarcoPublico>
  )

  const mm = String(Math.floor((restante ?? 0) / 60)).padStart(2, '0')
  const ss = String((restante ?? 0) % 60).padStart(2, '0')
  return (
    <MarcoPublico>
      <div className="sticky top-0 z-10 -mx-4 mb-6 flex items-center justify-between border-b border-slate-200 bg-slate-50/95 px-4 py-3 backdrop-blur">
        <h1 className="font-semibold text-slate-900">{p.titulo}</h1>
        <span className={cx('flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-sm', restante < 300 ? 'bg-rose-100 text-rose-700' : 'bg-white text-slate-700 ring-1 ring-slate-200')}>
          <Timer className="h-4 w-4" />{mm}:{ss}</span>
      </div>
      <div className="space-y-5">
        {p.preguntas.map((q, i) => (
          <div key={q.id} className="card p-6">
            <p className="mb-3 font-medium text-slate-900">{i + 1}. {q.enunciado} <span className="text-xs font-normal text-slate-400">({q.puntos} pts)</span></p>
            {q.tipo === 'opcion_multiple' ? (
              <div className="space-y-2">
                {q.opciones.map((o, j) => (
                  <label key={j} className={cx('flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm',
                    resp[q.id]?.opcion === j ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:bg-slate-50')}>
                    <input type="radio" name={`q${q.id}`} className="accent-brand-600" checked={resp[q.id]?.opcion === j} onChange={() => setResp({ ...resp, [q.id]: { opcion: j } })} />{o}
                  </label>
                ))}
              </div>
            ) : (
              <>
                {q.ejemplo && <p className="mb-2 font-mono text-xs text-slate-500">Ejemplo: {q.funcion}({q.ejemplo.entrada.map((x) => JSON.stringify(x)).join(', ')}) → {JSON.stringify(q.ejemplo.esperado)}</p>}
                <textarea spellCheck={false} rows={10} className="w-full rounded-lg bg-slate-900 p-4 font-mono text-sm text-slate-100 outline-none focus:ring-2 focus:ring-brand-500"
                  value={resp[q.id]?.codigo ?? q.plantilla_codigo ?? ''}
                  onChange={(e) => setResp({ ...resp, [q.id]: { codigo: e.target.value } })}
                  onKeyDown={(e) => {
                    if (e.key !== 'Tab') return
                    e.preventDefault()
                    const t = e.target; const s = t.selectionStart
                    const nuevo = `${t.value.slice(0, s)}    ${t.value.slice(t.selectionEnd)}`
                    setResp({ ...resp, [q.id]: { codigo: nuevo } })
                    requestAnimationFrame(() => { t.selectionStart = t.selectionEnd = s + 4 })
                  }} />
              </>
            )}
          </div>
        ))}
      </div>
      <Alerta>{error}</Alerta>
      <div className="mt-6 flex justify-end"><button className="btn-primary" disabled={enviando} onClick={enviar}>Enviar respuestas</button></div>
    </MarcoPublico>
  )
}
