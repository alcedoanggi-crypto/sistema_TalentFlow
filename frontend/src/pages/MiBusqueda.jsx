import { useRef, useState } from 'react'
import { Upload, Plus, Bell, ExternalLink, Lightbulb, Trash2, RefreshCw, Compass, CalendarClock, FileText } from 'lucide-react'
import { api } from '../api'
import { Alerta, Badge, Cargando, Campo, Encabezado, Kpi, Modal, ScoreRing, Vacio, useCarga, fecha, cx, MODALIDAD } from '../components/ui'
import { MatchDetalle } from '../components/acciones'

export const ESTADOS = {
  por_postular: ['Por postular', 'gris'], postulada: ['Postulada', 'azul'], en_proceso: ['En proceso', 'morado'],
  entrevista: ['Entrevista', 'marca'], oferta: ['Oferta', 'ambar'], aceptada: ['Aceptada', 'verde'],
  rechazada: ['Rechazada', 'rojo'], sin_respuesta: ['Sin respuesta', 'gris'],
}
const VACIA = { empresa: '', puesto: '', url: '', descripcion: '', modalidad: '', salario: '', estado: 'por_postular', fecha_postulacion: '', proximo_seguimiento: '', contacto: '', notas: '' }

export default function MiBusqueda() {
  const [cv, , , recargarCv] = useCarga(() => api.get('/personal/cv'), [])
  const [d, cargando, , recargar] = useCarga(() => api.get('/personal/postulaciones'), [])
  const [filtro, setFiltro] = useState('')
  const [abierta, setAbierta] = useState(null) // objeto o 'nueva'
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState('')
  const input = useRef()

  const subirCv = async (archivo) => {
    if (!archivo) return
    setSubiendo(true); setError('')
    const fd = new FormData(); fd.append('archivo', archivo)
    try { await api.put('/personal/cv', fd, { formData: true }); recargarCv(); recargar() } catch (e) { setError(e.message) } finally { setSubiendo(false) }
  }
  const completar = async (r) => { await api.patch(`/personal/recordatorios/${r.id}`, { completado: true }); recargar() }

  const lista = (d?.postulaciones || []).filter((p) => !filtro || p.estado === filtro)

  return (
    <div className="space-y-6">
      <Encabezado titulo="Mi búsqueda de empleo" subtitulo="Modo personal: registra las vacantes a las que te postulas, haz seguimiento y compara tu CV contra cada una.">
        <button className="btn-primary" onClick={() => setAbierta('nueva')}><Plus className="h-4 w-4" />Registrar vacante</button>
      </Encabezado>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card flex items-center gap-4 p-5">
          <div className="rounded-lg bg-brand-50 p-3 text-brand-600"><FileText className="h-6 w-6" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-slate-500">Mi CV</p>
            {cv ? <>
              <p className="truncate font-medium text-slate-900">{cv.nombre_original}</p>
              <p className="text-xs text-slate-500">{cv.datos?.experiencia_anios ?? 0} años detectados · actualizado {fecha(cv.actualizado_en)}</p>
            </> : <p className="text-sm text-slate-600">Súbelo para calcular tu compatibilidad.</p>}
          </div>
          <input ref={input} type="file" accept=".pdf,.docx" hidden onChange={(e) => subirCv(e.target.files[0])} />
          <button className="btn-secondary" disabled={subiendo} onClick={() => input.current.click()}><Upload className="h-4 w-4" />{cv ? 'Cambiar' : 'Subir'}</button>
        </div>
        <Kpi titulo="Tasa de respuesta" valor={d?.resumen.tasa_respuesta} sufijo="%" nota={`${d?.resumen.total ?? 0} vacantes registradas`} icono={Compass} />
        <Kpi titulo="Match promedio" valor={d?.resumen.match_promedio} sufijo="/100" tono="ambar" nota="Tu CV vs. las vacantes" />
      </div>
      <Alerta>{error}</Alerta>

      {d && (d.recordatorios.length > 0 || d.resumen.habilidades_a_reforzar.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card p-5">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900"><Bell className="h-4 w-4 text-amber-500" />Recordatorios pendientes</h3>
            {!d.recordatorios.length ? <p className="text-sm text-slate-500">Nada pendiente.</p> : (
              <ul className="space-y-2">
                {d.recordatorios.map((r) => (
                  <li key={r.id} className="flex items-start gap-3 text-sm">
                    <input type="checkbox" className="mt-1 accent-brand-600" onChange={() => completar(r)} />
                    <div className="flex-1">
                      <p className="text-slate-800">{r.texto}</p>
                      <p className={cx('text-xs', r.vencido ? 'font-medium text-rose-600' : 'text-slate-500')}>{fecha(r.fecha)} · {r.puesto} en {r.empresa}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="card p-5">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900"><Lightbulb className="h-4 w-4 text-brand-600" />Habilidades que más te piden y no tienes</h3>
            <div className="space-y-2">
              {d.resumen.habilidades_a_reforzar.map(([h, n]) => (
                <div key={h} className="flex items-center gap-3 text-sm">
                  <span className="w-32 truncate text-slate-700">{h}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-rose-400" style={{ width: `${(n / d.resumen.habilidades_a_reforzar[0][1]) * 100}%` }} /></div>
                  <span className="w-16 text-right text-xs text-slate-500">{n} vacante{n > 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div>
        <div className="mb-3 flex flex-wrap gap-1.5">
          <button onClick={() => setFiltro('')} className={cx('rounded-full px-3 py-1 text-xs ring-1 ring-inset', !filtro ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-600 ring-slate-200')}>Todas</button>
          {Object.entries(ESTADOS).map(([k, [t]]) => (
            <button key={k} onClick={() => setFiltro(k)} className={cx('rounded-full px-3 py-1 text-xs ring-1 ring-inset', filtro === k ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-600 ring-slate-200')}>
              {t} {d?.resumen.por_estado?.[k] ? <span className="opacity-60">{d.resumen.por_estado[k]}</span> : null}</button>
          ))}
        </div>
        {cargando && !d ? <Cargando /> : !lista.length ? <div className="card"><Vacio icono={Compass} titulo="Aún no registras vacantes" texto="Pega la descripción de una oferta y verás qué tanto encaja tu CV." /></div> : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {lista.map((p) => (
              <button key={p.id} onClick={() => setAbierta(p)} className="card flex gap-4 p-4 text-left transition hover:border-brand-200 hover:shadow-md">
                <ScoreRing score={p.match_score} size={48} grosor={5} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-900">{p.puesto}</p>
                  <p className="truncate text-sm text-slate-500">{p.empresa}{p.modalidad && ` · ${MODALIDAD[p.modalidad]}`}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <Badge tono={ESTADOS[p.estado][1]}>{ESTADOS[p.estado][0]}</Badge>
                    {p.proximo_seguimiento && <Badge tono={p.seguimiento_vencido ? 'rojo' : 'gris'}><CalendarClock className="h-3 w-3" />{fecha(p.proximo_seguimiento)}</Badge>}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {abierta && <Ficha p={abierta === 'nueva' ? null : abierta} tieneCv={!!cv} onCerrar={() => setAbierta(null)} onListo={recargar} />}
    </div>
  )
}

function Ficha({ p, tieneCv, onCerrar, onListo }) {
  const [f, setF] = useState(() => p ? Object.fromEntries(Object.keys(VACIA).map((k) => [k, p[k] ?? ''])) : VACIA)
  const [actual, setActual] = useState(p)
  const [rec, setRec] = useState({ fecha: '', texto: '' })
  const [error, setError] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const guardar = async (e) => {
    e.preventDefault(); setError('')
    const cuerpo = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === '' ? null : v]))
    cuerpo.estado ||= 'por_postular'
    try {
      const r = actual ? await api.put(`/personal/postulaciones/${actual.id}`, cuerpo) : await api.post('/personal/postulaciones', cuerpo)
      setActual(r); onListo()
    } catch (err) { setError(err.message) }
  }
  const borrar = async () => { await api.del(`/personal/postulaciones/${actual.id}`); onListo(); onCerrar() }
  const agregarRec = async (e) => {
    e.preventDefault()
    try { setActual(await api.post(`/personal/postulaciones/${actual.id}/recordatorios`, rec)); setRec({ fecha: '', texto: '' }); onListo() } catch (err) { setError(err.message) }
  }

  return (
    <Modal abierto onCerrar={onCerrar} titulo={actual ? `${actual.puesto} · ${actual.empresa}` : 'Registrar vacante'} ancho="max-w-4xl">
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <form onSubmit={guardar} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Empresa"><input className="input" required value={f.empresa} onChange={set('empresa')} /></Campo>
            <Campo label="Puesto"><input className="input" required value={f.puesto} onChange={set('puesto')} /></Campo>
            <Campo label="Estado">
              <select className="input" value={f.estado} onChange={set('estado')}>{Object.entries(ESTADOS).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}</select>
            </Campo>
            <Campo label="Modalidad">
              <select className="input" value={f.modalidad} onChange={set('modalidad')}><option value="">—</option>{Object.entries(MODALIDAD).map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>
            </Campo>
            <Campo label="Fecha de postulación"><input type="date" className="input" value={f.fecha_postulacion} onChange={set('fecha_postulacion')} /></Campo>
            <Campo label="Próximo seguimiento"><input type="date" className="input" value={f.proximo_seguimiento} onChange={set('proximo_seguimiento')} /></Campo>
            <Campo label="Salario"><input className="input" value={f.salario} onChange={set('salario')} /></Campo>
            <Campo label="Contacto"><input className="input" value={f.contacto} onChange={set('contacto')} placeholder="Reclutador/a" /></Campo>
          </div>
          <Campo label="Enlace a la oferta">
            <div className="flex gap-2">
              <input className="input" value={f.url} onChange={set('url')} />
              {f.url && <a href={f.url} target="_blank" rel="noreferrer" className="btn-secondary px-2.5"><ExternalLink className="h-4 w-4" /></a>}
            </div>
          </Campo>
          <Campo label="Descripción de la oferta (pégala completa para analizarla)"><textarea className="input text-xs" rows={7} value={f.descripcion} onChange={set('descripcion')} /></Campo>
          <Campo label="Notas"><textarea className="input" rows={2} value={f.notas} onChange={set('notas')} /></Campo>
          <Alerta>{error}</Alerta>
          <div className="flex items-center justify-between">
            {actual ? <button type="button" className="btn-ghost text-rose-600" onClick={borrar}><Trash2 className="h-4 w-4" />Eliminar</button> : <span />}
            <button className="btn-primary">{actual ? 'Guardar y reanalizar' : 'Guardar y analizar'}</button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">Mi CV vs. esta vacante</h3>
              {actual && <button className="btn-ghost p-1" title="Reanalizar" onClick={async () => setActual(await api.post(`/personal/postulaciones/${actual.id}/analizar`))}><RefreshCw className="h-3.5 w-3.5" /></button>}
            </div>
            {!tieneCv ? <p className="text-sm text-slate-500">Sube tu CV para ver tu compatibilidad.</p>
              : actual?.match_detalle ? <>
                <MatchDetalle detalle={actual.match_detalle} score={actual.match_score} compacto />
                {actual.match_detalle.sugerencias?.length > 0 && (
                  <ul className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
                    {actual.match_detalle.sugerencias.map((s, i) => <li key={i} className="flex gap-2 text-xs text-slate-600"><Lightbulb className="h-3.5 w-3.5 shrink-0 text-amber-500" />{s}</li>)}
                  </ul>
                )}
              </> : <p className="text-sm text-slate-500">Pega la descripción y guarda para analizar.</p>}
          </div>
          {actual && (
            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-900">Recordatorios</h3>
              <ul className="mb-3 space-y-1">
                {actual.recordatorios.map((r) => (
                  <li key={r.id} className={cx('text-xs', r.completado ? 'text-slate-400 line-through' : 'text-slate-700')}>{fecha(r.fecha)} · {r.texto}</li>
                ))}
              </ul>
              <form onSubmit={agregarRec} className="space-y-2">
                <input type="date" required className="input" value={rec.fecha} onChange={(e) => setRec({ ...rec, fecha: e.target.value })} />
                <input required className="input" placeholder="Ej. Escribir al reclutador" value={rec.texto} onChange={(e) => setRec({ ...rec, texto: e.target.value })} />
                <button className="btn-secondary w-full"><Bell className="h-4 w-4" />Agregar</button>
              </form>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
