import { useEffect, useState } from 'react'
import { X, Loader2, Check, Minus, Plus } from 'lucide-react'

export const cx = (...c) => c.filter(Boolean).join(' ')

export function Spinner({ className = '' }) {
  return <Loader2 className={cx('animate-spin text-brand-600', className || 'h-5 w-5')} />
}

export function Cargando({ texto = 'Cargando…' }) {
  return <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-500"><Spinner /> {texto}</div>
}

export function Vacio({ icono: Icono, titulo, texto, children }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      {Icono && <div className="mb-3 rounded-full bg-slate-100 p-3"><Icono className="h-6 w-6 text-slate-400" /></div>}
      <p className="font-medium text-slate-700">{titulo}</p>
      {texto && <p className="mt-1 max-w-sm text-sm text-slate-500">{texto}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}

export function Encabezado({ titulo, subtitulo, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{titulo}</h1>
        {subtitulo && <p className="mt-1 text-sm text-slate-500">{subtitulo}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}

const TONOS = {
  gris: 'bg-slate-100 text-slate-700 ring-slate-200',
  verde: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  rojo: 'bg-rose-50 text-rose-700 ring-rose-200',
  azul: 'bg-sky-50 text-sky-700 ring-sky-200',
  ambar: 'bg-amber-50 text-amber-800 ring-amber-200',
  morado: 'bg-violet-50 text-violet-700 ring-violet-200',
  marca: 'bg-brand-50 text-brand-700 ring-brand-100',
}

export function Badge({ tono = 'gris', children, className = '' }) {
  return <span className={cx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset', TONOS[tono], className)}>{children}</span>
}

/** Chip de habilidad: verde = cumple, rojo = falta, gris = adicional. */
export function Chip({ estado = 'neutral', children, titulo }) {
  const estilos = {
    cumple: 'bg-emerald-50 text-emerald-800 ring-emerald-300',
    falta: 'bg-rose-50 text-rose-700 ring-rose-200 line-through decoration-rose-300',
    deseable: 'bg-sky-50 text-sky-800 ring-sky-300',
    neutral: 'bg-slate-50 text-slate-600 ring-slate-200',
  }
  const Icono = estado === 'cumple' || estado === 'deseable' ? Check : estado === 'falta' ? Minus : Plus
  return (
    <span title={titulo} className={cx('inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset', estilos[estado])}>
      <Icono className="h-3 w-3 shrink-0" />{children}
    </span>
  )
}

export function colorScore(s) {
  if (s == null) return '#94a3b8'
  if (s >= 75) return '#059669'
  if (s >= 50) return '#d97706'
  return '#e11d48'
}

export function ScoreRing({ score, size = 56, grosor = 6, etiqueta = true }) {
  const r = (size - grosor) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(100, score ?? 0))
  return (
    <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={grosor} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={colorScore(score)} strokeWidth={grosor}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c - (v / 100) * c} className="transition-all duration-700" />
      </svg>
      {etiqueta && <span className="absolute font-semibold tabular-nums" style={{ fontSize: size * 0.27, color: colorScore(score) }}>
        {score == null ? '—' : Math.round(score)}</span>}
    </div>
  )
}

export function Modal({ abierto, onCerrar, titulo, children, ancho = 'max-w-lg' }) {
  useEffect(() => {
    if (!abierto) return
    const f = (e) => e.key === 'Escape' && onCerrar()
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [abierto, onCerrar])
  if (!abierto) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 pt-[8vh] backdrop-blur-sm" onMouseDown={onCerrar}>
      <div className={cx('card w-full p-6', ancho)} onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{titulo}</h2>
          <button className="btn-ghost p-1.5" onClick={onCerrar} aria-label="Cerrar"><X className="h-4 w-4" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Alerta({ tipo = 'error', children }) {
  if (!children) return null
  const t = { error: 'border-rose-200 bg-rose-50 text-rose-700', ok: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    info: 'border-sky-200 bg-sky-50 text-sky-800' }[tipo]
  return <div className={cx('rounded-lg border px-3 py-2 text-sm', t)}>{children}</div>
}

export function Campo({ label, children, className = '' }) {
  return <label className={cx('block', className)}><span className="label">{label}</span>{children}</label>
}

export function Kpi({ titulo, valor, sufijo, icono: Icono, nota, tono = 'brand' }) {
  const tonos = { brand: 'bg-brand-50 text-brand-600', verde: 'bg-emerald-50 text-emerald-600', ambar: 'bg-amber-50 text-amber-600', rosa: 'bg-rose-50 text-rose-600' }
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-500">{titulo}</p>
        {Icono && <div className={cx('rounded-lg p-2', tonos[tono])}><Icono className="h-4 w-4" /></div>}
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">{valor ?? '—'}<span className="ml-1 text-base font-normal text-slate-400">{valor != null && sufijo}</span></p>
      {nota && <p className="mt-1 text-xs text-slate-500">{nota}</p>}
    </div>
  )
}

/** Hook simple de carga: [datos, cargando, error, recargar] */
export function useCarga(fn, deps = []) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null })
  const [n, setN] = useState(0)
  useEffect(() => {
    let vivo = true
    setEstado((e) => ({ ...e, cargando: true }))
    fn().then((d) => vivo && setEstado({ datos: d, cargando: false, error: null }))
      .catch((e) => vivo && setEstado({ datos: null, cargando: false, error: e.message }))
    return () => { vivo = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, n])
  return [estado.datos, estado.cargando, estado.error, () => setN((x) => x + 1)]
}

export const fecha = (iso, conHora = false) => iso ? new Date(iso).toLocaleString('es', conHora
  ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
  : { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const hace = (iso) => {
  const d = Math.round((Date.now() - new Date(iso)) / 86400000)
  return d <= 0 ? 'hoy' : d === 1 ? 'ayer' : `hace ${d} días`
}

export const MODALIDAD = { remoto: 'Remoto', hibrido: 'Híbrido', presencial: 'Presencial' }
export const FUENTE = { portal_empleo: 'Página de empleos', computrabajo: 'Computrabajo', linkedin: 'LinkedIn', indeed: 'Indeed', bumeran: 'Bumeran', occ: 'OCC Mundial', elempleo: 'elempleo.com', glassdoor: 'Glassdoor', referido: 'Referido', evento: 'Evento', otro: 'Otro' }
export const dinero = (v, moneda) => v == null ? null : new Intl.NumberFormat('es', { style: 'currency', currency: moneda, maximumFractionDigits: 0 }).format(v)
