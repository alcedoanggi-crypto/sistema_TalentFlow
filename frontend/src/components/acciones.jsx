/** Componentes reutilizados entre páginas: detalle del match, CV resaltado y modales de acción. */
import { useMemo, useState } from 'react'
import { Star } from 'lucide-react'
import { api } from '../api'
import { Alerta, Campo, Chip, Modal, ScoreRing, useCarga, cx } from './ui'

// ------------------------------------------------------------- match ---

const NOMBRE_COMPONENTE = { obligatorias: 'Obligatorias', deseables: 'Deseables', experiencia: 'Experiencia' }

export function MatchDetalle({ detalle, score, compacto = false }) {
  if (!detalle) return <p className="text-sm text-slate-500">Sin análisis de compatibilidad.</p>
  const o = detalle.obligatorias || { cumple: [], faltan: [] }
  const d = detalle.deseables || { cumple: [], faltan: [] }
  const exp = detalle.experiencia
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreRing score={score ?? detalle.score} size={compacto ? 56 : 72} grosor={compacto ? 6 : 7} />
        <div className="flex-1 space-y-1.5">
          {Object.keys(NOMBRE_COMPONENTE).filter((k) => detalle.componentes?.[k] != null).map((k) => [k, detalle.componentes[k]]).map(([k, v]) => (
            <div key={k} className="flex items-center gap-2 text-xs">
              <span className="w-24 text-slate-500">{NOMBRE_COMPONENTE[k]} <span className="text-slate-400">({detalle.pesos?.[k]}%)</span></span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-brand-500" style={{ width: `${v}%` }} />
              </div>
              <span className="w-10 text-right tabular-nums text-slate-600">{Math.round(v)}%</span>
            </div>
          ))}
        </div>
      </div>
      <Grupo titulo={`Obligatorias · ${o.cumple.length}/${o.cumple.length + o.faltan.length}`}>
        {o.cumple.map((h) => <Chip key={h} estado="cumple" titulo="Cumple">{h}</Chip>)}
        {o.faltan.map((h) => <Chip key={h} estado="falta" titulo="Le falta">{h}</Chip>)}
      </Grupo>
      {(d.cumple.length + d.faltan.length) > 0 && (
        <Grupo titulo={`Deseables · ${d.cumple.length}/${d.cumple.length + d.faltan.length}`}>
          {d.cumple.map((h) => <Chip key={h} estado="deseable" titulo="Cumple">{h}</Chip>)}
          {d.faltan.map((h) => <Chip key={h} estado="neutral" titulo="No la tiene">{h}</Chip>)}
        </Grupo>
      )}
      {exp && (
        <p className="text-xs text-slate-600">
          Experiencia: <b className={exp.cumple ? 'text-emerald-700' : 'text-rose-600'}>{exp.candidato} años</b> de {exp.requerida} requeridos
        </p>
      )}
      {!compacto && detalle.adicionales?.length > 0 && (
        <Grupo titulo="Otras habilidades del candidato">
          {detalle.adicionales.map((h) => <Chip key={h}>{h}</Chip>)}
        </Grupo>
      )}
    </div>
  )
}

function Grupo({ titulo, children }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">{titulo}</p>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  )
}

export function Leyenda() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-slate-500">
      <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" />Cumple</span>
      <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-rose-300" />Le falta</span>
      <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-sky-400" />Deseable que cumple</span>
    </div>
  )
}

// --------------------------------------------------------- CV resaltado ---

/** Quita acentos carácter por carácter para conservar las posiciones del texto original. */
const plano = (s) => Array.from(s, (c) => c.normalize('NFD')[0].toLowerCase()).join('')
const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/**
 * Resalta en el texto del CV las palabras que generaron cada habilidad.
 * `terminos` = { "postgres": "PostgreSQL", ... } (forma normalizada → habilidad canónica).
 * `requeridas` = set de nombres canónicos que pide la vacante (se pintan en verde).
 */
export function CvResaltado({ texto, terminos, requeridas }) {
  const partes = useMemo(() => {
    const claves = Object.keys(terminos || {}).sort((a, b) => b.length - a.length)
    if (!texto || !claves.length) return [{ t: texto || '' }]
    const re = new RegExp(`(?<![\\p{L}\\p{N}])(${claves.map(escapar).join('|')})(?![\\p{L}\\p{N}])`, 'gu')
    const base = plano(texto)
    const out = []
    let ultimo = 0
    for (const m of base.matchAll(re)) {
      if (m.index > ultimo) out.push({ t: texto.slice(ultimo, m.index) })
      out.push({ t: texto.slice(m.index, m.index + m[0].length), h: terminos[m[0]] })
      ultimo = m.index + m[0].length
    }
    out.push({ t: texto.slice(ultimo) })
    return out
  }, [texto, terminos])

  return (
    <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-700">
      {partes.map((p, i) => p.h ? (
        <span key={i} title={p.h} className={cx('rounded px-0.5 font-medium',
          requeridas?.has(p.h) ? 'bg-emerald-100 text-emerald-900' : 'bg-slate-200/70 text-slate-900')}>{p.t}</span>
      ) : p.t)}
    </pre>
  )
}

// ------------------------------------------------------------ modales ---

const TIPOS_ENTREVISTA = { tecnica: 'Técnica', rh: 'Recursos Humanos', cultural: 'Cultural', final: 'Final' }
export { TIPOS_ENTREVISTA }

function aIsoConZona(local) {
  // "2026-11-10T10:00" (hora local del navegador) → ISO con offset, que exige la API.
  const d = new Date(local)
  const off = -d.getTimezoneOffset()
  const s = off >= 0 ? '+' : '-'
  const pad = (n) => String(Math.floor(Math.abs(n))).padStart(2, '0')
  return `${local}:00${s}${pad(off / 60)}:${pad(off % 60)}`
}

export function ProgramarEntrevista({ abierto, onCerrar, postulaciones, onListo }) {
  const [usuarios] = useCarga(() => api.get('/usuarios'), [])
  const [f, setF] = useState({ postulacion_id: '', tipo: 'tecnica', inicio: '', duracion_min: 60, lugar: '', notas: '', entrevistadores: [] })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const pid = f.postulacion_id || postulaciones?.[0]?.id

  const guardar = async (e) => {
    e.preventDefault(); setError(''); setEnviando(true)
    try {
      await api.post('/entrevistas', { ...f, postulacion_id: +pid, duracion_min: +f.duracion_min, inicio: aIsoConZona(f.inicio) })
      onListo?.(); onCerrar()
    } catch (err) { setError(err.message) } finally { setEnviando(false) }
  }
  const alternar = (id) => setF({ ...f, entrevistadores: f.entrevistadores.includes(id) ? f.entrevistadores.filter((x) => x !== id) : [...f.entrevistadores, id] })

  return (
    <Modal abierto={abierto} onCerrar={onCerrar} titulo="Programar entrevista">
      <form onSubmit={guardar} className="space-y-3">
        {postulaciones?.length > 1 && (
          <Campo label="Postulación">
            <select className="input" value={pid} onChange={set('postulacion_id')}>
              {postulaciones.map((p) => <option key={p.id} value={p.id}>{p.nombre ? `${p.nombre} · ` : ''}{p.vacante?.titulo || p.vacante}</option>)}
            </select>
          </Campo>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Tipo">
            <select className="input" value={f.tipo} onChange={set('tipo')}>
              {Object.entries(TIPOS_ENTREVISTA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Campo>
          <Campo label="Duración (min)"><input type="number" min={15} step={15} className="input" value={f.duracion_min} onChange={set('duracion_min')} /></Campo>
        </div>
        <Campo label="Fecha y hora"><input type="datetime-local" required className="input" value={f.inicio} onChange={set('inicio')} /></Campo>
        <Campo label="Lugar o enlace de videollamada"><input className="input" value={f.lugar} onChange={set('lugar')} placeholder="https://meet.google.com/…" /></Campo>
        <div>
          <span className="label">Entrevistadores</span>
          <div className="flex flex-wrap gap-1.5">
            {usuarios?.map((u) => (
              <button type="button" key={u.id} onClick={() => alternar(u.id)}
                className={cx('rounded-full px-3 py-1 text-xs ring-1 ring-inset', f.entrevistadores.includes(u.id) ? 'bg-brand-600 text-white ring-brand-600' : 'bg-white text-slate-600 ring-slate-300')}>
                {u.nombre}</button>
            ))}
          </div>
        </div>
        <p className="text-xs text-slate-500">Se enviará una invitación por correo con un archivo .ics al candidato y a cada entrevistador.</p>
        <Alerta>{error}</Alerta>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onCerrar}>Cancelar</button>
          <button className="btn-primary" disabled={enviando || !f.entrevistadores.length || !f.inicio}>Programar y enviar invitación</button>
        </div>
      </form>
    </Modal>
  )
}

const RECOMENDACIONES = { fuerte_si: 'Contratar sin duda', si: 'Contratar', no: 'No contratar', fuerte_no: 'Definitivamente no' }
export { RECOMENDACIONES }

export function Evaluar({ entrevista, onCerrar, onListo }) {
  const [competencias] = useCarga(() => api.get('/competencias'), [])
  const [puntajes, setPuntajes] = useState({})
  const [f, setF] = useState({ recomendacion: '', fortalezas: '', areas_mejora: '' })
  const [error, setError] = useState('')

  const guardar = async (e) => {
    e.preventDefault(); setError('')
    try {
      await api.post(`/entrevistas/${entrevista.id}/evaluaciones`, {
        ...f, puntajes: Object.entries(puntajes).map(([id, p]) => ({ competencia_id: +id, puntaje: p })),
      })
      onListo?.(); onCerrar()
    } catch (err) { setError(err.message) }
  }

  return (
    <Modal abierto={!!entrevista} onCerrar={onCerrar} titulo={`Evaluar a ${entrevista?.candidato}`} ancho="max-w-xl">
      <form onSubmit={guardar} className="space-y-4">
        <div className="space-y-2">
          {competencias?.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800">{c.nombre}</p>
                {c.descripcion && <p className="truncate text-xs text-slate-500">{c.descripcion}</p>}
              </div>
              <div className="flex shrink-0">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button type="button" key={n} onClick={() => setPuntajes({ ...puntajes, [c.id]: n })} aria-label={`${n} de 5`}>
                    <Star className={cx('h-5 w-5', n <= (puntajes[c.id] || 0) ? 'fill-amber-400 text-amber-400' : 'text-slate-300')} />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <Campo label="Recomendación">
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(RECOMENDACIONES).map(([k, v]) => (
              <button type="button" key={k} onClick={() => setF({ ...f, recomendacion: k })}
                className={cx('rounded-lg px-3 py-2 text-sm ring-1 ring-inset', f.recomendacion === k
                  ? (k.includes('no') ? 'bg-rose-50 text-rose-700 ring-rose-300' : 'bg-emerald-50 text-emerald-700 ring-emerald-300')
                  : 'ring-slate-200 text-slate-600')}>{v}</button>
            ))}
          </div>
        </Campo>
        <Campo label="Fortalezas"><textarea className="input" rows={2} value={f.fortalezas} onChange={(e) => setF({ ...f, fortalezas: e.target.value })} /></Campo>
        <Campo label="Áreas de mejora"><textarea className="input" rows={2} value={f.areas_mejora} onChange={(e) => setF({ ...f, areas_mejora: e.target.value })} /></Campo>
        <Alerta>{error}</Alerta>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onCerrar}>Cancelar</button>
          <button className="btn-primary" disabled={!f.recomendacion || !Object.keys(puntajes).length}>Guardar evaluación</button>
        </div>
      </form>
    </Modal>
  )
}

export function AsignarPrueba({ abierto, onCerrar, postulaciones, onListo }) {
  const [pruebas] = useCarga(() => api.get('/pruebas'), [])
  const [prueba, setPrueba] = useState('')
  const [pid, setPid] = useState('')
  const [dias, setDias] = useState(5)
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')

  const enviar = async () => {
    setError('')
    try {
      setRes(await api.post('/pruebas/asignar', { prueba_id: +(prueba || pruebas[0].id), postulacion_id: +(pid || postulaciones[0].id), dias_vigencia: +dias }))
      onListo?.()
    } catch (e) { setError(e.message) }
  }
  const cerrar = () => { setRes(null); onCerrar() }

  return (
    <Modal abierto={abierto} onCerrar={cerrar} titulo="Enviar prueba técnica">
      {res ? (
        <div className="space-y-3">
          <Alerta tipo="ok">Prueba enviada por correo al candidato.</Alerta>
          <Campo label="Enlace único"><input readOnly className="input" value={res.enlace} onFocus={(e) => e.target.select()} /></Campo>
          <div className="flex justify-end"><button className="btn-primary" onClick={cerrar}>Listo</button></div>
        </div>
      ) : (
        <div className="space-y-3">
          {postulaciones?.length > 1 && (
            <Campo label="Postulación">
              <select className="input" value={pid} onChange={(e) => setPid(e.target.value)}>
                {postulaciones.map((p) => <option key={p.id} value={p.id}>{p.vacante.titulo}</option>)}
              </select>
            </Campo>
          )}
          <Campo label="Prueba">
            <select className="input" value={prueba} onChange={(e) => setPrueba(e.target.value)}>
              {pruebas?.map((p) => <option key={p.id} value={p.id}>{p.titulo} · {p.preguntas.length} preguntas · {p.tiempo_limite_min} min</option>)}
            </select>
          </Campo>
          <Campo label="Días de vigencia"><input type="number" min={1} max={30} className="input" value={dias} onChange={(e) => setDias(e.target.value)} /></Campo>
          <Alerta>{error}</Alerta>
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={cerrar}>Cancelar</button>
            <button className="btn-primary" disabled={!pruebas?.length} onClick={enviar}>Enviar enlace</button>
          </div>
        </div>
      )}
    </Modal>
  )
}

export function EnviarCorreo({ abierto, onCerrar, postulaciones, onListo }) {
  const [plantillas] = useCarga(() => api.get('/plantillas'), [])
  const [pid, setPid] = useState('')
  const [codigo, setCodigo] = useState('')
  const [asunto, setAsunto] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [error, setError] = useState('')

  const elegir = (c) => {
    setCodigo(c)
    const p = plantillas.plantillas.find((x) => x.codigo === c)
    setAsunto(p?.asunto || ''); setCuerpo(p?.cuerpo || '')
  }
  const enviar = async () => {
    setError('')
    try {
      await api.post('/correos', { postulacion_id: +(pid || postulaciones[0].id), plantilla: codigo || null, asunto, cuerpo })
      onListo?.(); onCerrar()
    } catch (e) { setError(e.message) }
  }

  return (
    <Modal abierto={abierto} onCerrar={onCerrar} titulo="Enviar correo" ancho="max-w-xl">
      <div className="space-y-3">
        {postulaciones?.length > 1 && (
          <Campo label="Postulación">
            <select className="input" value={pid} onChange={(e) => setPid(e.target.value)}>
              {postulaciones.map((p) => <option key={p.id} value={p.id}>{p.vacante.titulo}</option>)}
            </select>
          </Campo>
        )}
        <Campo label="Plantilla">
          <select className="input" value={codigo} onChange={(e) => elegir(e.target.value)}>
            <option value="">— Mensaje libre —</option>
            {plantillas?.plantillas.map((p) => <option key={p.codigo} value={p.codigo}>{p.nombre}</option>)}
          </select>
        </Campo>
        <Campo label="Asunto"><input className="input" value={asunto} onChange={(e) => setAsunto(e.target.value)} /></Campo>
        <Campo label="Mensaje"><textarea className="input font-mono text-xs" rows={9} value={cuerpo} onChange={(e) => setCuerpo(e.target.value)} /></Campo>
        <p className="text-xs text-slate-500">Las variables como <code>{'{{candidato}}'}</code> o <code>{'{{vacante}}'}</code> se reemplazan al enviar.</p>
        <Alerta>{error}</Alerta>
        <div className="flex justify-end gap-2">
          <button className="btn-secondary" onClick={onCerrar}>Cancelar</button>
          <button className="btn-primary" disabled={!asunto || !cuerpo} onClick={enviar}>Enviar</button>
        </div>
      </div>
    </Modal>
  )
}
