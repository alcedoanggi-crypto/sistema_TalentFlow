import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, Mail, Phone, Linkedin, Download, CalendarPlus, FileCode2, Send, Trash2, X, Plus, ShieldCheck, Star,
} from 'lucide-react'
import { api, descargar } from '../api'
import { useAuth } from '../auth'
import { Alerta, Badge, Cargando, Modal, useCarga, fecha, cx, FUENTE } from '../components/ui'
import {
  AsignarPrueba, CvResaltado, EnviarCorreo, Evaluar, Leyenda, MatchDetalle, ProgramarEntrevista, RECOMENDACIONES,
  TIPOS_ENTREVISTA,
} from '../components/acciones'

const PESTANAS = [['match', 'Compatibilidad'], ['cv', 'CV analizado'], ['entrevistas', 'Entrevistas'], ['pruebas', 'Pruebas'], ['correos', 'Correos']]

export default function CandidatoDetalle() {
  const { id } = useParams()
  const navegar = useNavigate()
  const { puede, usuario } = useAuth()
  const gestion = puede('admin', 'reclutador')
  const [c, cargando, error, recargar] = useCarga(() => api.get(`/candidatos/${id}`), [id])
  const [pestana, setPestana] = useState('match')
  const [sel, setSel] = useState(0) // postulación seleccionada
  const [modal, setModal] = useState(null)
  const [evaluando, setEvaluando] = useState(null)
  const [nuevaHab, setNuevaHab] = useState('')
  const [msg, setMsg] = useState('')

  const p = c?.postulaciones[sel]
  const requeridas = useMemo(() => new Set([
    ...(p?.match_detalle?.obligatorias?.cumple || []), ...(p?.match_detalle?.deseables?.cumple || []),
  ]), [p])

  if (cargando && !c) return <Cargando />
  if (error) return <Alerta>{error}</Alerta>

  const agregarHab = async (e) => {
    e.preventDefault(); setMsg('')
    try { await api.post(`/candidatos/${id}/habilidades`, { nombre: nuevaHab }); setNuevaHab(''); recargar() } catch (err) { setMsg(err.message) }
  }
  const quitarHab = async (hid) => { await api.del(`/candidatos/${id}/habilidades/${hid}`); recargar() }
  const borrar = async () => { await api.del(`/candidatos/${id}`); navegar('/candidatos') }

  return (
    <div>
      <Link to="/candidatos" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" />Candidatos</Link>

      {/* Cabecera */}
      <div className="card mb-6 p-6">
        <div className="flex flex-wrap items-start gap-5">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-100 text-lg font-semibold text-brand-700">
            {c.nombre.split(' ').map((x) => x[0]).slice(0, 2).join('')}
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{c.nombre}</h1>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
              <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{c.email}</span>
              {c.telefono && <span className="flex items-center gap-1"><Phone className="h-3.5 w-3.5" />{c.telefono}</span>}
              {c.linkedin && <a href={c.linkedin.startsWith('http') ? c.linkedin : `https://${c.linkedin}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-brand-600"><Linkedin className="h-3.5 w-3.5" />LinkedIn</a>}
              <span>{c.experiencia_anios} años de experiencia</span>
            </div>
            {c.anonimizado && <div className="mt-2"><Badge tono="rojo">Datos anonimizados</Badge></div>}
          </div>
          <div className="flex flex-wrap gap-2">
            {c.cv && <button className="btn-secondary" onClick={() => descargar(`/documentos/${c.cv.id}/descargar`, c.cv.nombre)}><Download className="h-4 w-4" />CV</button>}
            {gestion && !c.anonimizado && c.postulaciones.length > 0 && <>
              <button className="btn-secondary" onClick={() => setModal('entrevista')}><CalendarPlus className="h-4 w-4" />Entrevista</button>
              <button className="btn-secondary" onClick={() => setModal('prueba')}><FileCode2 className="h-4 w-4" />Prueba</button>
              <button className="btn-secondary" onClick={() => setModal('correo')}><Send className="h-4 w-4" />Correo</button>
            </>}
            {puede('admin') && !c.anonimizado && <button className="btn-ghost text-rose-600" onClick={() => setModal('borrar')} title="Borrar datos"><Trash2 className="h-4 w-4" /></button>}
          </div>
        </div>

        {/* Habilidades detectadas: resaltadas si coinciden con la vacante seleccionada */}
        <div className="mt-5 border-t border-slate-100 pt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Habilidades ({c.habilidades.length})</p>
            <Leyenda />
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {c.habilidades.map((h) => (
              <span key={h.id} title={h.origen === 'manual' ? 'Agregada manualmente' : 'Extraída del CV'}
                className={cx('group inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset',
                  requeridas.has(h.nombre) ? 'bg-emerald-50 text-emerald-800 ring-emerald-300' : 'bg-slate-50 text-slate-600 ring-slate-200')}>
                {h.nombre}{h.origen === 'manual' && <span className="text-slate-400">*</span>}
                {gestion && <button onClick={() => quitarHab(h.id)} className="hidden text-slate-400 hover:text-rose-600 group-hover:inline"><X className="h-3 w-3" /></button>}
              </span>
            ))}
            {gestion && !c.anonimizado && (
              <form onSubmit={agregarHab} className="flex items-center gap-1">
                <input value={nuevaHab} onChange={(e) => setNuevaHab(e.target.value)} placeholder="Agregar…" className="w-28 rounded-md border border-dashed border-slate-300 px-2 py-1 text-xs outline-none focus:border-brand-500" />
                {nuevaHab && <button className="text-brand-600"><Plus className="h-4 w-4" /></button>}
              </form>
            )}
          </div>
          {msg && <p className="mt-2 text-xs text-rose-600">{msg}</p>}
        </div>
      </div>

      {/* Selector de postulación */}
      {c.postulaciones.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {c.postulaciones.map((x, i) => (
            <button key={x.id} onClick={() => setSel(i)} className={cx('rounded-lg px-3 py-1.5 text-sm ring-1 ring-inset', i === sel ? 'bg-brand-600 text-white ring-brand-600' : 'bg-white text-slate-600 ring-slate-200')}>
              {x.vacante.titulo}</button>
          ))}
        </div>
      )}

      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200">
        {PESTANAS.map(([k, t]) => (
          <button key={k} onClick={() => setPestana(k)} className={cx('-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium',
            pestana === k ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800')}>{t}</button>
        ))}
      </div>

      {pestana === 'match' && (
        p ? (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="card p-6 lg:col-span-2">
              <h2 className="mb-1 font-semibold text-slate-900">{p.vacante.titulo}</h2>
              <p className="mb-5 text-sm text-slate-500">Etapa actual: <b>{p.etapa_nombre}</b> · Fuente: {FUENTE[p.fuente] || p.fuente}</p>
              <MatchDetalle detalle={p.match_detalle} score={p.match_score} />
              {p.carta && <div className="mt-6 border-t border-slate-100 pt-4"><p className="mb-1 text-xs font-medium uppercase text-slate-400">Carta de presentación</p><p className="whitespace-pre-line text-sm text-slate-700">{p.carta}</p></div>}
            </div>
            <div className="card p-6">
              <h3 className="mb-4 font-semibold text-slate-900">Historial</h3>
              <ol className="relative space-y-4 border-l border-slate-200 pl-4">
                {p.historial.map((h, i) => (
                  <li key={i} className="text-sm">
                    <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-500" />
                    <p className="font-medium text-slate-800">{h.hasta}</p>
                    <p className="text-xs text-slate-500">{fecha(h.fecha, true)} · {h.usuario}</p>
                    {h.comentario && <p className="mt-1 text-xs italic text-slate-600">«{h.comentario}»</p>}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : <div className="card p-6 text-sm text-slate-500">Sin postulaciones.</div>
      )}

      {pestana === 'cv' && (
        c.cv ? (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="card space-y-4 p-6 text-sm">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">Datos extraídos</h3>
                <Badge tono="morado">motor: {c.cv.datos?.motor}</Badge>
              </div>
              {c.cv.datos?.perfil && <Bloque t="Perfil"><p className="text-slate-700">{c.cv.datos.perfil}</p></Bloque>}
              <Bloque t="Experiencia">
                {c.cv.datos?.experiencia?.length ? c.cv.datos.experiencia.map((e, i) => (
                  <p key={i} className="text-slate-700">{e.puesto} <span className="text-xs text-slate-400">· {e.periodo}</span></p>
                )) : <p className="text-slate-400">No detectada</p>}
              </Bloque>
              <Bloque t="Educación">
                {c.cv.datos?.educacion?.length ? c.cv.datos.educacion.map((e, i) => <p key={i} className="text-slate-700">{e}</p>) : <p className="text-slate-400">No detectada</p>}
              </Bloque>
              {c.cv.datos?.idiomas?.length > 0 && <Bloque t="Idiomas"><p className="text-slate-700">{c.cv.datos.idiomas.join(' · ')}</p></Bloque>}
              {c.cv.datos?.organizaciones?.length > 0 && <Bloque t="Organizaciones (spaCy NER)"><div className="flex flex-wrap gap-1">{c.cv.datos.organizaciones.map((o) => <Badge key={o}>{o}</Badge>)}</div></Bloque>}
            </div>
            <div className="card p-6 lg:col-span-2">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">{c.cv.nombre}</h3>
                <span className="text-xs text-slate-500"><span className="rounded bg-emerald-100 px-1">verde</span> = requerida por la vacante</span>
              </div>
              <CvResaltado texto={c.cv.texto} terminos={c.cv.terminos} requeridas={requeridas} />
            </div>
          </div>
        ) : <div className="card p-6 text-sm text-slate-500">No hay CV disponible.</div>
      )}

      {pestana === 'entrevistas' && (
        <div className="space-y-3">
          {!c.entrevistas.length && <div className="card p-6 text-sm text-slate-500">Sin entrevistas programadas.</div>}
          {c.entrevistas.map((e) => {
            const puedoEvaluar = e.entrevistadores.some((x) => x.id === usuario.id) || puede('admin')
            return (
              <div key={e.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">Entrevista {TIPOS_ENTREVISTA[e.tipo].toLowerCase()} · {e.vacante}</p>
                    <p className="text-sm text-slate-500">{fecha(e.inicio, true)} · {e.duracion_min} min · {e.entrevistadores.map((x) => x.nombre).join(', ')}</p>
                  </div>
                  <div className="flex gap-2">
                    <Badge tono={e.estado === 'programada' ? 'azul' : e.estado === 'realizada' ? 'verde' : 'gris'}>{e.estado}</Badge>
                    <button className="btn-ghost px-2 py-1 text-xs" onClick={() => descargar(`/entrevistas/${e.id}/ics`, 'entrevista.ics')}>.ics</button>
                    {puedoEvaluar && e.estado !== 'cancelada' && <button className="btn-secondary px-2.5 py-1 text-xs" onClick={() => setEvaluando(e)}>Evaluar</button>}
                  </div>
                </div>
                {e.evaluaciones.map((ev) => (
                  <div key={ev.id} className="mt-4 rounded-lg bg-slate-50 p-4">
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                      <b className="text-slate-800">{ev.evaluador}</b>
                      <Badge tono={ev.recomendacion.includes('no') ? 'rojo' : 'verde'}>{RECOMENDACIONES[ev.recomendacion]}</Badge>
                      <span className="ml-auto flex items-center gap-1 text-amber-600"><Star className="h-4 w-4 fill-amber-400 text-amber-400" />{ev.promedio}</span>
                    </div>
                    <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
                      {ev.puntajes.map((pt) => (
                        <div key={pt.competencia_id} className="flex items-center justify-between text-xs">
                          <span className="text-slate-600">{pt.competencia}</span>
                          <span className="flex">{[1, 2, 3, 4, 5].map((n) => <Star key={n} className={cx('h-3 w-3', n <= pt.puntaje ? 'fill-amber-400 text-amber-400' : 'text-slate-300')} />)}</span>
                        </div>
                      ))}
                    </div>
                    {ev.fortalezas && <p className="mt-2 text-xs text-slate-600"><b>Fortalezas:</b> {ev.fortalezas}</p>}
                    {ev.areas_mejora && <p className="text-xs text-slate-600"><b>A mejorar:</b> {ev.areas_mejora}</p>}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      )}

      {pestana === 'pruebas' && (
        <div className="card divide-y divide-slate-100">
          {!c.pruebas.length && <p className="p-6 text-sm text-slate-500">No se han enviado pruebas.</p>}
          {c.pruebas.map((a) => (
            <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-medium text-slate-800">{a.prueba}</p>
                <p className="text-xs text-slate-500">Enviada {fecha(a.enviada_en)} · vence {fecha(a.expira_en)}</p>
              </div>
              {a.completada_en
                ? <div className="text-right"><p className="font-semibold tabular-nums">{a.puntaje} / {a.puntaje_max}</p><Badge tono={a.aprobada ? 'verde' : 'rojo'}>{a.aprobada ? 'Aprobada' : 'No aprobada'}</Badge></div>
                : <Badge tono="ambar">Pendiente</Badge>}
            </div>
          ))}
        </div>
      )}

      {pestana === 'correos' && (
        <div className="space-y-2">
          {!c.correos.length && <div className="card p-6 text-sm text-slate-500">Sin correos.</div>}
          {c.correos.map((m) => (
            <details key={m.id} className="card group p-4">
              <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 text-sm">
                <span className="font-medium text-slate-800">{m.asunto}</span>
                {m.adjunto && <Badge tono="morado">{m.adjunto}</Badge>}
                <Badge tono={m.estado === 'enviado' ? 'verde' : m.estado === 'error' ? 'rojo' : 'gris'}>{m.estado}</Badge>
                <span className="ml-auto text-xs text-slate-400">{fecha(m.enviado_en, true)}</span>
              </summary>
              <pre className="mt-3 whitespace-pre-wrap font-sans text-sm text-slate-600">{m.cuerpo}</pre>
            </details>
          ))}
        </div>
      )}

      <div className="mt-6 flex items-center gap-2 text-xs text-slate-400">
        <ShieldCheck className="h-3.5 w-3.5" />
        Consentimiento v{c.privacidad.version} otorgado el {fecha(c.privacidad.consentimiento_en)} · datos conservados hasta {fecha(c.privacidad.retener_hasta)}
      </div>

      <ProgramarEntrevista abierto={modal === 'entrevista'} onCerrar={() => setModal(null)} postulaciones={c.postulaciones} onListo={recargar} />
      <AsignarPrueba abierto={modal === 'prueba'} onCerrar={() => setModal(null)} postulaciones={c.postulaciones} onListo={recargar} />
      <EnviarCorreo abierto={modal === 'correo'} onCerrar={() => setModal(null)} postulaciones={c.postulaciones} onListo={recargar} />
      {evaluando && <Evaluar entrevista={evaluando} onCerrar={() => setEvaluando(null)} onListo={recargar} />}
      <Modal abierto={modal === 'borrar'} onCerrar={() => setModal(null)} titulo="Borrar datos del candidato">
        <p className="text-sm text-slate-600">Se eliminará el CV y se anonimizarán nombre, contacto y texto extraído. Las métricas agregadas (embudo, tiempos) se conservan sin datos personales. Esta acción no se puede deshacer.</p>
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
          <button className="btn-danger" onClick={borrar}>Borrar definitivamente</button>
        </div>
      </Modal>
    </div>
  )
}

function Bloque({ t, children }) {
  return <div><p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">{t}</p><div className="space-y-1">{children}</div></div>
}
