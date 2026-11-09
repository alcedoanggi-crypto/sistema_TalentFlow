import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Paperclip, Save } from 'lucide-react'
import { api } from '../api'
import { Alerta, Badge, Cargando, Campo, Encabezado, Vacio, useCarga, fecha, cx } from '../components/ui'

export default function Comunicacion() {
  const [pestana, setPestana] = useState('plantillas')
  return (
    <div>
      <Encabezado titulo="Comunicación con candidatos" subtitulo="Plantillas reutilizables y registro de todos los correos enviados." />
      <div className="mb-4 flex w-fit gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        {[['plantillas', 'Plantillas'], ['bandeja', 'Correos enviados']].map(([k, t]) => (
          <button key={k} onClick={() => setPestana(k)} className={cx('rounded-md px-3 py-1.5', pestana === k ? 'bg-white font-medium shadow-sm' : 'text-slate-600')}>{t}</button>
        ))}
      </div>
      {pestana === 'plantillas' ? <Plantillas /> : <Bandeja />}
    </div>
  )
}

function Plantillas() {
  const [datos, cargando, , recargar] = useCarga(() => api.get('/plantillas'), [])
  const [sel, setSel] = useState(null)
  const [f, setF] = useState(null)
  const [vista, setVista] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => { if (datos && !sel) setSel(datos.plantillas[0]?.codigo) }, [datos, sel])
  useEffect(() => {
    const p = datos?.plantillas.find((x) => x.codigo === sel)
    if (p) { setF({ nombre: p.nombre, asunto: p.asunto, cuerpo: p.cuerpo }); setMsg(null) }
  }, [sel, datos])
  useEffect(() => {
    if (!f || !sel) return
    const t = setTimeout(() => api.post(`/plantillas/${sel}/vista-previa`, { asunto: f.asunto, cuerpo: f.cuerpo }).then(setVista).catch(() => {}), 300)
    return () => clearTimeout(t)
  }, [f, sel])

  if (cargando || !f) return <Cargando />
  const guardar = async () => {
    try { await api.put(`/plantillas/${sel}`, f); setMsg({ tipo: 'ok', t: 'Plantilla guardada.' }); recargar() } catch (e) { setMsg({ tipo: 'error', t: e.message }) }
  }
  const insertar = (v) => setF({ ...f, cuerpo: `${f.cuerpo}{{${v}}}` })

  return (
    <div className="grid gap-6 lg:grid-cols-[14rem_1fr]">
      <nav className="card h-fit p-2">
        {datos.plantillas.map((p) => (
          <button key={p.codigo} onClick={() => setSel(p.codigo)} className={cx('block w-full rounded-lg px-3 py-2 text-left text-sm', sel === p.codigo ? 'bg-brand-50 font-medium text-brand-700' : 'text-slate-600 hover:bg-slate-50')}>
            {p.nombre}</button>
        ))}
      </nav>
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="card space-y-3 p-5">
          <Campo label="Nombre"><input className="input" value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} /></Campo>
          <Campo label="Asunto"><input className="input" value={f.asunto} onChange={(e) => setF({ ...f, asunto: e.target.value })} /></Campo>
          <Campo label="Cuerpo"><textarea className="input font-mono text-xs" rows={12} value={f.cuerpo} onChange={(e) => setF({ ...f, cuerpo: e.target.value })} /></Campo>
          <div>
            <span className="label">Variables disponibles (clic para insertar)</span>
            <div className="flex flex-wrap gap-1">
              {datos.variables.map((v) => <button key={v} onClick={() => insertar(v)} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600 hover:bg-brand-50 hover:text-brand-700">{`{{${v}}}`}</button>)}
            </div>
          </div>
          {msg && <Alerta tipo={msg.tipo}>{msg.t}</Alerta>}
          <div className="flex justify-end"><button className="btn-primary" onClick={guardar}><Save className="h-4 w-4" />Guardar</button></div>
        </div>
        <div className="card h-fit p-5">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">Vista previa con datos de ejemplo</p>
          {vista && (
            <div className="rounded-lg border border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-sm"><span className="text-slate-400">Asunto: </span><b>{vista.asunto}</b></div>
              <pre className="whitespace-pre-wrap p-4 font-sans text-sm text-slate-700">{vista.cuerpo}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Bandeja() {
  const [lista, cargando] = useCarga(() => api.get('/correos'), [])
  if (cargando) return <Cargando />
  if (!lista.length) return <div className="card"><Vacio icono={Mail} titulo="No se han enviado correos" /></div>
  return (
    <div className="space-y-2">
      <Alerta tipo="info">Sin servidor SMTP configurado, los correos quedan como <b>simulado</b> y se registran aquí con su contenido completo.</Alerta>
      {lista.map((m) => (
        <details key={m.id} className="card p-4">
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-slate-800">{m.asunto}</span>
            {m.plantilla && <Badge>{m.plantilla}</Badge>}
            {m.adjunto && <Badge tono="morado"><Paperclip className="h-3 w-3" />{m.adjunto}</Badge>}
            <Badge tono={m.estado === 'enviado' ? 'verde' : m.estado === 'error' ? 'rojo' : 'gris'}>{m.estado}</Badge>
            <span className="ml-auto text-xs text-slate-400">{m.para} · {fecha(m.enviado_en, true)}</span>
          </summary>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm text-slate-600">{m.cuerpo}</pre>
          {m.error && <p className="mt-2 text-xs text-rose-600">{m.error}</p>}
          {m.candidato_id && <Link to={`/candidatos/${m.candidato_id}`} className="mt-2 inline-block text-xs text-brand-600">Ver candidato →</Link>}
        </details>
      ))}
    </div>
  )
}
