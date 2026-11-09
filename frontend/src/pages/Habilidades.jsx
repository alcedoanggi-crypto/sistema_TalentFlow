import { useState } from 'react'
import { Plus, Search, X, Tags } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Alerta, Badge, Cargando, Campo, Encabezado, Modal, Vacio, useCarga } from '../components/ui'

const CATEGORIAS = { tecnica: 'Técnica', blanda: 'Blanda', idioma: 'Idioma', herramienta: 'Herramienta' }

export default function Habilidades() {
  const { puede } = useAuth()
  const gestion = puede('admin', 'reclutador')
  const [lista, cargando, , recargar] = useCarga(() => api.get('/habilidades'), [])
  const [buscar, setBuscar] = useState('')
  const [probar, setProbar] = useState('')
  const [resultado, setResultado] = useState(null)
  const [nueva, setNueva] = useState(false)
  const [error, setError] = useState('')

  const resolver = async (e) => {
    e.preventDefault()
    setResultado(await api.get(`/habilidades/resolver?q=${encodeURIComponent(probar)}`))
  }
  const agregarSin = async (h, valor) => {
    setError('')
    try { await api.post(`/habilidades/${h.id}/sinonimos`, { sinonimo: valor }); recargar() } catch (e) { setError(e.message) }
  }
  const quitarSin = async (sid) => { await api.del(`/habilidades/sinonimos/${sid}`); recargar() }

  const filtradas = (lista || []).filter((h) => !buscar || h.nombre.toLowerCase().includes(buscar.toLowerCase())
    || h.sinonimos.some((s) => s.sinonimo.includes(buscar.toLowerCase())))

  return (
    <div>
      <Encabezado titulo="Catálogo de habilidades" subtitulo="Tabla normalizada con sinónimos: «JS», «Postgres» o «k8s» se reconocen como su habilidad canónica al analizar CVs y vacantes.">
        {gestion && <button className="btn-primary" onClick={() => setNueva(true)}><Plus className="h-4 w-4" />Nueva habilidad</button>}
      </Encabezado>

      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input pl-9" placeholder="Filtrar catálogo…" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <form onSubmit={resolver} className="flex gap-2">
          <input className="input" placeholder="Probar un término: JS, postgres, react.js…" value={probar} onChange={(e) => { setProbar(e.target.value); setResultado(null) }} />
          <button className="btn-secondary whitespace-nowrap" disabled={!probar}>Resolver</button>
        </form>
      </div>
      {resultado && (
        <div className="mb-4">
          <Alerta tipo={resultado.habilidad ? 'ok' : 'error'}>
            {resultado.habilidad ? <>«{resultado.termino}» → <b>{resultado.habilidad.nombre}</b></> : <>«{resultado.termino}» no está en el catálogo.</>}
          </Alerta>
        </div>
      )}
      <Alerta>{error}</Alerta>

      {cargando ? <Cargando /> : !filtradas.length ? <div className="card"><Vacio icono={Tags} titulo="Sin resultados" /></div> : (
        <div className="card divide-y divide-slate-100">
          {filtradas.map((h) => (
            <div key={h.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <div className="w-48">
                <p className="font-medium text-slate-900">{h.nombre}</p>
                <p className="text-xs text-slate-400">{CATEGORIAS[h.categoria] || h.categoria} · {h.usos} usos</p>
              </div>
              <div className="flex flex-1 flex-wrap items-center gap-1">
                {h.sinonimos.map((s) => (
                  <Badge key={s.id} className="group font-mono">
                    {s.sinonimo}
                    {gestion && <button onClick={() => quitarSin(s.id)} className="hidden text-slate-400 hover:text-rose-600 group-hover:inline"><X className="h-3 w-3" /></button>}
                  </Badge>
                ))}
                {gestion && <AgregarSinonimo onAgregar={(v) => agregarSin(h, v)} />}
              </div>
            </div>
          ))}
        </div>
      )}
      {nueva && <NuevaHabilidad onCerrar={() => setNueva(false)} onListo={recargar} />}
    </div>
  )
}

function AgregarSinonimo({ onAgregar }) {
  const [v, setV] = useState('')
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (v.trim()) { onAgregar(v.trim()); setV('') } }}>
      <input value={v} onChange={(e) => setV(e.target.value)} placeholder="+ sinónimo" className="w-24 rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-xs outline-none focus:border-brand-500" />
    </form>
  )
}

function NuevaHabilidad({ onCerrar, onListo }) {
  const [f, setF] = useState({ nombre: '', categoria: 'tecnica', sinonimos: '' })
  const [error, setError] = useState('')
  const guardar = async (e) => {
    e.preventDefault()
    try {
      await api.post('/habilidades', { ...f, sinonimos: f.sinonimos.split(',').map((s) => s.trim()).filter(Boolean) })
      onListo(); onCerrar()
    } catch (err) { setError(err.message) }
  }
  return (
    <Modal abierto onCerrar={onCerrar} titulo="Nueva habilidad">
      <form onSubmit={guardar} className="space-y-3">
        <Campo label="Nombre canónico"><input className="input" required value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} placeholder="Ej. TypeScript" /></Campo>
        <Campo label="Categoría">
          <select className="input" value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })}>
            {Object.entries(CATEGORIAS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Campo>
        <Campo label="Sinónimos (separados por coma)"><input className="input" value={f.sinonimos} onChange={(e) => setF({ ...f, sinonimos: e.target.value })} placeholder="ts, type script" /></Campo>
        <Alerta>{error}</Alerta>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onCerrar}>Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </Modal>
  )
}
