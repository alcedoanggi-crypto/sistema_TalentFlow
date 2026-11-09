import { useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Upload, CheckCircle2, Briefcase, Clock } from 'lucide-react'
import { api } from '../../api'
import { Alerta, Badge, Cargando, Campo, Vacio, useCarga, MODALIDAD, FUENTE, dinero, Spinner } from '../../components/ui'
import { MarcoPublico } from './Empleos'

export default function VacantePublica() {
  const { slug, vslug } = useParams()
  // ?fuente=computrabajo → el enlace pegado en el aviso de cada portal registra de dónde llegó el candidato
  const [params] = useSearchParams()
  const fuenteUrl = FUENTE[params.get('fuente')] ? params.get('fuente') : null
  const [v, cargando, error] = useCarga(() => api.get(`/publico/empresas/${slug}/vacantes/${vslug}`, { publico: true }), [slug, vslug])
  const [aviso] = useCarga(() => api.get('/publico/aviso-privacidad', { publico: true }), [])
  const [f, setF] = useState({ nombre: '', email: '', telefono: '', linkedin: '', fuente: fuenteUrl || 'portal_empleo', carta: '', consentimiento: false })
  const [cv, setCv] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [res, setRes] = useState(null)
  const [err, setErr] = useState('')
  const input = useRef()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  if (cargando) return <Cargando />
  if (error) return <MarcoPublico><Vacio icono={Briefcase} titulo="La vacante no existe o ya cerró" /></MarcoPublico>

  const enviar = async (e) => {
    e.preventDefault(); setErr(''); setEnviando(true)
    const fd = new FormData()
    Object.entries(f).forEach(([k, val]) => fd.append(k, val))
    fd.append('cv', cv)
    try { setRes(await api.post(`/publico/empresas/${slug}/vacantes/${vslug}/postular`, fd, { publico: true, formData: true })) } catch (e2) { setErr(e2.message) } finally { setEnviando(false) }
  }

  const obligatorias = v.habilidades.filter((h) => h.tipo === 'obligatoria')
  const deseables = v.habilidades.filter((h) => h.tipo === 'deseable')

  return (
    <MarcoPublico empresa={v.empresa}>
      <Link to={`/empleos/${slug}`} className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" />Todas las vacantes</Link>
      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <article className="card p-6">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{v.titulo}</h1>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-slate-500">
            <span className="flex items-center gap-1"><MapPin className="h-4 w-4" />{v.ubicacion}</span>
            <Badge tono="marca">{MODALIDAD[v.modalidad]}</Badge>
            {v.experiencia_min_anios > 0 && <Badge><Clock className="h-3 w-3" />{v.experiencia_min_anios}+ años</Badge>}
          </div>
          {v.salario_min != null && <p className="mt-3 text-lg font-medium text-slate-800">{dinero(v.salario_min, v.moneda)} – {dinero(v.salario_max, v.moneda)} <span className="text-sm font-normal text-slate-500">mensual</span></p>}
          <div className="mt-6 whitespace-pre-line text-slate-700">{v.descripcion}</div>
          {v.requisitos && <><h2 className="mt-6 mb-2 font-semibold text-slate-900">Requisitos</h2><div className="whitespace-pre-line text-slate-700">{v.requisitos}</div></>}
          <h2 className="mt-6 mb-2 font-semibold text-slate-900">Habilidades</h2>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1.5"><span className="mr-1 text-sm text-slate-500">Obligatorias:</span>{obligatorias.map((h) => <Badge key={h.id} tono="marca">{h.nombre}</Badge>)}</div>
            {deseables.length > 0 && <div className="flex flex-wrap gap-1.5"><span className="mr-1 text-sm text-slate-500">Deseables:</span>{deseables.map((h) => <Badge key={h.id}>{h.nombre}</Badge>)}</div>}
          </div>
        </article>

        <aside className="card h-fit p-6 lg:sticky lg:top-6">
          {res ? (
            <div className="text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-500" />
              <p className="mt-3 font-semibold text-slate-900">{res.mensaje}</p>
              <Link to={res.portal} className="btn-primary mt-4 w-full">Ver mi portal</Link>
            </div>
          ) : (
            <form onSubmit={enviar} className="space-y-3">
              <h2 className="font-semibold text-slate-900">Postúlate</h2>
              <Campo label="Nombre completo *"><input className="input" required minLength={3} value={f.nombre} onChange={set('nombre')} /></Campo>
              <Campo label="Correo *"><input type="email" className="input" required value={f.email} onChange={set('email')} /></Campo>
              <Campo label="Teléfono"><input className="input" value={f.telefono} onChange={set('telefono')} /></Campo>
              <Campo label="LinkedIn"><input className="input" value={f.linkedin} onChange={set('linkedin')} /></Campo>
              {!fuenteUrl && (
                <Campo label="¿Cómo te enteraste?">
                  <select className="input" value={f.fuente} onChange={set('fuente')}>{Object.entries(FUENTE).map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>
                </Campo>
              )}
              <div>
                <span className="label">CV (PDF o Word, máx. 5 MB) *</span>
                <input ref={input} type="file" accept=".pdf,.docx" hidden onChange={(e) => setCv(e.target.files[0])} />
                <button type="button" onClick={() => input.current.click()} className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 px-3 py-4 text-sm text-slate-600 hover:border-brand-500 hover:text-brand-700">
                  <Upload className="h-4 w-4" />{cv ? cv.name : 'Seleccionar archivo'}</button>
              </div>
              <Campo label="Carta de presentación"><textarea className="input" rows={3} value={f.carta} onChange={set('carta')} /></Campo>
              <details className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                <summary className="cursor-pointer font-medium text-slate-700">Aviso de privacidad (v{aviso?.version})</summary>
                <ul className="mt-2 list-disc space-y-1 pl-4">{aviso?.texto.map((t, i) => <li key={i}>{t}</li>)}</ul>
              </details>
              <label className="flex items-start gap-2 text-xs text-slate-600">
                <input type="checkbox" className="mt-0.5 accent-brand-600" checked={f.consentimiento} onChange={(e) => setF({ ...f, consentimiento: e.target.checked })} />
                Acepto el tratamiento de mis datos personales según el aviso de privacidad.
              </label>
              <Alerta>{err}</Alerta>
              <button className="btn-primary w-full" disabled={enviando || !cv || !f.consentimiento}>{enviando ? <><Spinner className="h-4 w-4 text-white" />Analizando tu CV…</> : 'Enviar postulación'}</button>
            </form>
          )}
        </aside>
      </div>
    </MarcoPublico>
  )
}
