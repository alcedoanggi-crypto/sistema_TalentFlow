import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { X, Info } from 'lucide-react'
import { api } from '../api'
import { Alerta, Campo, Cargando, Encabezado, Spinner, cx } from '../components/ui'

const VACIA = { titulo: '', departamento: '', ubicacion: '', modalidad: 'remoto', tipo_contrato: 'tiempo_completo', descripcion: '',
  requisitos: '', experiencia_min_anios: 0, salario_min: '', salario_max: '', moneda: 'USD', mostrar_salario: true, estado: 'borrador', habilidades: [] }

function SelectorHabilidades({ tipo, valor, onChange, catalogo }) {
  const [texto, setTexto] = useState('')
  const propias = valor.filter((h) => h.tipo === tipo)
  const agregar = (nombre) => {
    nombre = nombre.trim()
    if (!nombre || valor.some((h) => h.nombre.toLowerCase() === nombre.toLowerCase())) return setTexto('')
    onChange([...valor, { nombre, tipo }]); setTexto('')
  }
  const sugerencias = texto ? catalogo.filter((c) => c.nombre.toLowerCase().includes(texto.toLowerCase())
    || c.sinonimos.some((s) => s.sinonimo.includes(texto.toLowerCase()))).slice(0, 6) : []
  return (
    <div>
      <div className={cx('flex min-h-11 flex-wrap gap-1.5 rounded-lg border bg-white p-2', tipo === 'obligatoria' ? 'border-brand-200' : 'border-slate-300')}>
        {propias.map((h) => (
          <span key={h.nombre} className={cx('inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
            tipo === 'obligatoria' ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-700')}>
            {h.nombre}<button type="button" onClick={() => onChange(valor.filter((x) => x !== h))}><X className="h-3 w-3" /></button>
          </span>
        ))}
        <div className="relative min-w-40 flex-1">
          <input className="w-full px-1 py-1 text-sm outline-none" placeholder="Escribe y presiona Enter…" value={texto}
            onChange={(e) => setTexto(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); agregar(sugerencias[0]?.nombre || texto) } }} />
          {sugerencias.length > 0 && (
            <div className="absolute z-10 mt-1 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              {sugerencias.map((s) => (
                <button type="button" key={s.id} onClick={() => agregar(s.nombre)} className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50">
                  {s.nombre} <span className="text-xs text-slate-400">{s.sinonimos.slice(0, 3).map((x) => x.sinonimo).filter((x) => x !== s.nombre.toLowerCase()).join(', ')}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function VacanteForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [f, setF] = useState(id ? null : VACIA)
  const [catalogo, setCatalogo] = useState([])
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    api.get('/habilidades').then(setCatalogo)
    if (id) api.get(`/vacantes/${id}`).then((v) => setF({ ...VACIA, ...v, salario_min: v.salario_min ?? '', salario_max: v.salario_max ?? '',
      habilidades: v.habilidades.map((h) => ({ nombre: h.nombre, tipo: h.tipo })) }))
  }, [id])
  if (!f) return <Cargando />
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const guardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError('')
    const datos = { ...f, salario_min: f.salario_min === '' ? null : +f.salario_min, salario_max: f.salario_max === '' ? null : +f.salario_max,
      experiencia_min_anios: +f.experiencia_min_anios }
    try {
      const v = id ? await api.put(`/vacantes/${id}`, datos) : await api.post('/vacantes', datos)
      nav(`/vacantes/${v.id}`)
    } catch (err) { setError(err.message) } finally { setGuardando(false) }
  }

  return (
    <form onSubmit={guardar} className="mx-auto max-w-4xl">
      <Encabezado titulo={id ? 'Editar vacante' : 'Nueva vacante'} subtitulo="Los requisitos alimentan el cálculo de compatibilidad con cada CV.">
        <button type="button" className="btn-secondary" onClick={() => nav(-1)}>Cancelar</button>
        <button className="btn-primary" disabled={guardando}>{guardando && <Spinner className="h-4 w-4 text-white" />}Guardar</button>
      </Encabezado>
      <div className="mb-4"><Alerta>{error}</Alerta></div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card space-y-4 p-6 lg:col-span-2">
          <Campo label="Título del puesto"><input className="input" value={f.titulo} onChange={set('titulo')} required minLength={3} /></Campo>
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo label="Departamento"><input className="input" value={f.departamento || ''} onChange={set('departamento')} /></Campo>
            <Campo label="Ubicación"><input className="input" value={f.ubicacion || ''} onChange={set('ubicacion')} /></Campo>
          </div>
          <Campo label="Descripción del rol"><textarea className="input min-h-28" value={f.descripcion} onChange={set('descripcion')} required minLength={10} /></Campo>
          <Campo label="Requisitos (texto libre)"><textarea className="input min-h-20" value={f.requisitos || ''} onChange={set('requisitos')} /></Campo>
          <div>
            <span className="label">Habilidades obligatorias <span className="text-slate-400">· 60% del match</span></span>
            <SelectorHabilidades tipo="obligatoria" valor={f.habilidades} onChange={(h) => setF({ ...f, habilidades: h })} catalogo={catalogo} />
          </div>
          <div>
            <span className="label">Habilidades deseables <span className="text-slate-400">· 25% del match</span></span>
            <SelectorHabilidades tipo="deseable" valor={f.habilidades} onChange={(h) => setF({ ...f, habilidades: h })} catalogo={catalogo} />
          </div>
          <p className="flex items-start gap-2 rounded-lg bg-sky-50 p-3 text-xs text-sky-800"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Los sinónimos se resuelven solos: si escribes «Postgres» se usará «PostgreSQL», y un CV que diga «JS» cumplirá «JavaScript». Al guardar se recalcula el match de todas las postulaciones.</p>
        </div>
        <div className="space-y-6">
          <div className="card space-y-4 p-6">
            <Campo label="Estado">
              <select className="input" value={f.estado} onChange={set('estado')}>
                <option value="borrador">Borrador</option><option value="publicada">Publicada</option><option value="cerrada">Cerrada</option>
              </select>
            </Campo>
            <Campo label="Modalidad">
              <div className="grid grid-cols-3 gap-1 rounded-lg bg-slate-100 p-1">
                {[['remoto', 'Remoto'], ['hibrido', 'Híbrido'], ['presencial', 'Presencial']].map(([v, t]) => (
                  <button type="button" key={v} onClick={() => setF({ ...f, modalidad: v })}
                    className={cx('rounded-md py-1.5 text-xs', f.modalidad === v ? 'bg-white font-medium shadow-sm' : 'text-slate-600')}>{t}</button>
                ))}
              </div>
            </Campo>
            <Campo label="Tipo de contrato">
              <select className="input" value={f.tipo_contrato} onChange={set('tipo_contrato')}>
                <option value="tiempo_completo">Tiempo completo</option><option value="medio_tiempo">Medio tiempo</option>
                <option value="por_proyecto">Por proyecto</option><option value="practicas">Prácticas</option>
              </select>
            </Campo>
            <Campo label="Experiencia mínima (años) · 15% del match">
              <input className="input" type="number" min={0} max={40} step={0.5} value={f.experiencia_min_anios} onChange={set('experiencia_min_anios')} />
            </Campo>
          </div>
          <div className="card space-y-4 p-6">
            <div className="grid grid-cols-2 gap-3">
              <Campo label="Salario mín."><input className="input" type="number" min={0} value={f.salario_min} onChange={set('salario_min')} /></Campo>
              <Campo label="Salario máx."><input className="input" type="number" min={0} value={f.salario_max} onChange={set('salario_max')} /></Campo>
            </div>
            <Campo label="Moneda">
              <select className="input" value={f.moneda} onChange={set('moneda')}>
                {['USD', 'MXN', 'COP', 'PEN', 'CLP', 'ARS', 'EUR'].map((m) => <option key={m}>{m}</option>)}
              </select>
            </Campo>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.mostrar_salario} onChange={set('mostrar_salario')} />Mostrar salario en la página pública</label>
          </div>
        </div>
      </div>
    </form>
  )
}
