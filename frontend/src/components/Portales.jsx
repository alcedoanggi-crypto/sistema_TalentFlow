/** Panel "Portales de empleo" de una vacante: enlaces por portal + importación masiva de CV. */
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Copy, Check, Upload, CheckCircle2, XCircle, Info } from 'lucide-react'
import { api } from '../api'
import { Alerta, Badge, Campo, Modal, Spinner, useCarga, cx, FUENTE, colorScore } from './ui'

const PASOS_COMPUTRABAJO = [
  'Publica el aviso en Computrabajo (o el portal que uses) y pega el enlace de abajo en la descripción: «Postúlate aquí».',
  'Para quienes se postulen dentro del portal: entra a tu panel de empresa, abre la oferta y descarga los CV de los candidatos.',
  'Súbelos en «Importar CV»: TalentFlow lee cada CV, crea al candidato, calcula su match y lo pone en «Postulado».',
]

export default function Portales({ vacanteId, abierto, onCerrar, onImportado }) {
  const [d] = useCarga(() => (abierto ? api.get(`/vacantes/${vacanteId}/portales`) : Promise.resolve(null)), [vacanteId, abierto])
  const [pestana, setPestana] = useState('enlaces')
  const [copiado, setCopiado] = useState('')

  const copiar = async (texto, clave) => {
    try { await navigator.clipboard.writeText(texto) } catch { /* sin permiso de portapapeles */ }
    setCopiado(clave); setTimeout(() => setCopiado(''), 1500)
  }

  return (
    <Modal abierto={abierto} onCerrar={onCerrar} titulo="Portales de empleo" ancho="max-w-2xl">
      <div className="mb-4 flex w-fit gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        {[['enlaces', 'Enlaces por portal'], ['importar', 'Importar CV']].map(([k, t]) => (
          <button key={k} onClick={() => setPestana(k)} className={cx('rounded-md px-3 py-1.5', pestana === k ? 'bg-white font-medium shadow-sm' : 'text-slate-600')}>{t}</button>
        ))}
      </div>

      {pestana === 'enlaces' ? (
        !d ? <Spinner /> : (
          <div className="space-y-4">
            {!d.publicada && <Alerta tipo="error">La vacante no está publicada: los enlaces no funcionarán hasta publicarla.</Alerta>}
            <details className="rounded-lg bg-sky-50 p-3 text-sm text-sky-900">
              <summary className="flex cursor-pointer items-center gap-2 font-medium"><Info className="h-4 w-4" />¿Cómo traer las postulaciones de Computrabajo?</summary>
              <ol className="mt-2 list-decimal space-y-1 pl-5">{PASOS_COMPUTRABAJO.map((p) => <li key={p}>{p}</li>)}</ol>
              <p className="mt-2 text-xs text-sky-800">Computrabajo y la mayoría de portales no ofrecen una API pública para leer postulantes, y extraerlos con un robot viola sus términos de uso. Estas dos vías son las legítimas.</p>
            </details>
            <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {d.portales.map((p) => (
                <div key={p.codigo} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="w-32 shrink-0">
                    <p className="text-sm font-medium text-slate-800">{p.nombre}</p>
                    <p className="text-xs text-slate-400">{p.postulaciones} postulaciones</p>
                  </div>
                  <code className="min-w-0 flex-1 truncate rounded bg-slate-50 px-2 py-1 text-xs text-slate-600">{p.enlace}</code>
                  <button className="btn-secondary shrink-0 px-2.5 py-1 text-xs" onClick={() => copiar(p.enlace, p.codigo)}>
                    {copiado === p.codigo ? <><Check className="h-3.5 w-3.5 text-emerald-600" />Copiado</> : <><Copy className="h-3.5 w-3.5" />Copiar</>}
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500">Cada enlace registra automáticamente la fuente; en el Dashboard verás qué portal trae mejores candidatos.</p>
          </div>
        )
      ) : <Importar vacanteId={vacanteId} onImportado={onImportado} />}
    </Modal>
  )
}

function Importar({ vacanteId, onImportado }) {
  const [fuente, setFuente] = useState('computrabajo')
  const [archivos, setArchivos] = useState([])
  const [arrastrando, setArrastrando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')
  const input = useRef()

  const agregar = (lista) => setArchivos((a) => [...a, ...Array.from(lista).filter((f) => /\.(pdf|docx)$/i.test(f.name))].slice(0, 50))
  const importar = async () => {
    setEnviando(true); setError(''); setRes(null)
    const fd = new FormData()
    fd.append('fuente', fuente)
    archivos.forEach((f) => fd.append('archivos', f))
    try {
      const r = await api.post(`/vacantes/${vacanteId}/importar`, fd, { formData: true })
      setRes(r); setArchivos([])
      if (r.importados) onImportado?.()
    } catch (e) { setError(e.message) } finally { setEnviando(false) }
  }

  return (
    <div className="space-y-4">
      <Campo label="¿De qué portal vienen estos CV?">
        <select className="input" value={fuente} onChange={(e) => setFuente(e.target.value)}>
          {Object.entries(FUENTE).filter(([k]) => k !== 'portal_empleo').map(([k, t]) => <option key={k} value={k}>{t}</option>)}
        </select>
      </Campo>
      <div onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }} onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); agregar(e.dataTransfer.files) }}
        onClick={() => input.current.click()}
        className={cx('cursor-pointer rounded-xl border-2 border-dashed px-4 py-8 text-center transition',
          arrastrando ? 'border-brand-500 bg-brand-50' : 'border-slate-300 hover:border-brand-400')}>
        <Upload className="mx-auto h-6 w-6 text-slate-400" />
        <p className="mt-2 text-sm font-medium text-slate-700">Arrastra aquí los CV o haz clic para elegirlos</p>
        <p className="text-xs text-slate-500">PDF o Word · hasta 50 archivos · el correo se extrae del CV</p>
        <input ref={input} type="file" multiple accept=".pdf,.docx" hidden onChange={(e) => { agregar(e.target.files); e.target.value = '' }} />
      </div>
      {archivos.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {archivos.map((f, i) => <Badge key={i}>{f.name}</Badge>)}
        </div>
      )}
      <Alerta>{error}</Alerta>
      {res && (
        <div className="space-y-2">
          <Alerta tipo={res.importados ? 'ok' : 'error'}>{res.importados} de {res.total} CV importados. Cada candidato recibió el correo de «postulación recibida» con el enlace a su portal.</Alerta>
          <div className="max-h-60 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
            {res.resultados.map((r, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 text-sm">
                {r.ok ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" /> : <XCircle className="h-4 w-4 shrink-0 text-rose-500" />}
                {r.ok ? <Link to={`/candidatos/${r.candidato_id}`} className="font-medium text-slate-800 hover:text-brand-700">{r.nombre}</Link>
                  : <span className="truncate text-slate-700">{r.archivo}</span>}
                <span className="ml-auto text-xs" style={r.ok ? { color: colorScore(r.match_score) } : undefined}>
                  {r.ok ? `match ${Math.round(r.match_score)}` : <span className="text-rose-600">{r.error}</span>}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="flex justify-end">
        <button className="btn-primary" disabled={!archivos.length || enviando} onClick={importar}>
          {enviando ? <><Spinner className="h-4 w-4 text-white" />Analizando {archivos.length} CV…</> : `Importar ${archivos.length || ''} CV`}
        </button>
      </div>
    </div>
  )
}
