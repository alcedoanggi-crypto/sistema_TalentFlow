import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, ExternalLink, Pencil, Share2 } from 'lucide-react'
import Portales from '../components/Portales'
import { api } from '../api'
import { useAuth } from '../auth'
import { Alerta, Badge, Cargando, Campo, Encabezado, Modal, ScoreRing, useCarga, FUENTE, MODALIDAD, hace, cx } from '../components/ui'

export default function Pipeline() {
  const { id } = useParams()
  const { puede, usuario } = useAuth()
  const editable = puede('admin', 'reclutador')
  const [datos, cargando, error, recargar] = useCarga(() => api.get(`/vacantes/${id}/pipeline`), [id])
  const [arrastrando, setArrastrando] = useState(null)
  const [sobre, setSobre] = useState(null)
  const [descarte, setDescarte] = useState(null) // { tarjeta } pendiente de motivo
  const [motivo, setMotivo] = useState('')
  const [notificar, setNotificar] = useState(true)
  const [aviso, setAviso] = useState('')
  const [portales, setPortales] = useState(false)

  if (cargando && !datos) return <Cargando />
  if (error) return <Alerta>{error}</Alerta>
  const { vacante, columnas } = datos

  const mover = async (tarjeta, etapa, comentario) => {
    try {
      await api.patch(`/postulaciones/${tarjeta.id}/mover`, { etapa, comentario, notificar })
      setAviso(notificar ? `${tarjeta.nombre} movido. Se envió el correo de avance al candidato.` : `${tarjeta.nombre} movido.`)
      recargar()
    } catch (e) { setAviso(e.message) }
  }

  const soltar = (etapa) => {
    const t = arrastrando
    setArrastrando(null); setSobre(null)
    if (!t || t.etapa === etapa) return
    if (etapa === 'descartado') { setDescarte(t); setMotivo(''); return }
    mover(t, etapa)
  }

  return (
    <div>
      <Link to="/vacantes" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" />Vacantes</Link>
      <Encabezado titulo={vacante.titulo}
        subtitulo={`${vacante.ubicacion || ''} · ${MODALIDAD[vacante.modalidad]} · ${columnas.reduce((n, c) => n + c.tarjetas.length, 0)} candidatos`}>
        {vacante.estado === 'publicada' && (
          <a className="btn-secondary" target="_blank" rel="noreferrer" href={`/empleos/${usuario.empresa.slug}/${vacante.slug}`}>
            <ExternalLink className="h-4 w-4" />Ver publicación</a>)}
        {editable && <button className="btn-primary" onClick={() => setPortales(true)}><Share2 className="h-4 w-4" />Portales de empleo</button>}
        {editable && <Link to={`/vacantes/${id}/editar`} className="btn-secondary"><Pencil className="h-4 w-4" />Editar</Link>}
      </Encabezado>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500">{editable ? 'Arrastra las tarjetas entre columnas para avanzar a los candidatos.' : 'Vista de solo lectura.'}</p>
        {editable && <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={notificar} onChange={(e) => setNotificar(e.target.checked)} className="accent-brand-600" />
          Notificar al candidato por correo</label>}
      </div>
      {aviso && <div className="mb-3"><Alerta tipo="info">{aviso}</Alerta></div>}

      <div className="-mx-4 overflow-x-auto px-4 pb-4">
        <div className="flex min-w-max gap-3">
          {columnas.map((col) => (
            <div key={col.codigo}
              onDragOver={(e) => { if (editable) { e.preventDefault(); setSobre(col.codigo) } }}
              onDragLeave={() => setSobre((s) => (s === col.codigo ? null : s))}
              onDrop={() => soltar(col.codigo)}
              className={cx('flex w-64 flex-col rounded-xl bg-slate-100/80 p-2 transition',
                sobre === col.codigo && 'bg-brand-50 ring-2 ring-brand-500/40')}>
              <div className="flex items-center gap-2 px-2 py-2">
                <span className="h-2 w-2 rounded-full" style={{ background: col.color }} />
                <span className="text-sm font-semibold text-slate-700">{col.nombre}</span>
                <span className="ml-auto rounded-full bg-white px-2 text-xs tabular-nums text-slate-500">{col.tarjetas.length}</span>
              </div>
              <div className="flex min-h-24 flex-col gap-2">
                {col.tarjetas.map((t) => (
                  <div key={t.id} draggable={editable && !t.anonimizado}
                    onDragStart={() => setArrastrando(t)} onDragEnd={() => { setArrastrando(null); setSobre(null) }}
                    className={cx('rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition',
                      editable && 'cursor-grab active:cursor-grabbing hover:border-brand-200',
                      arrastrando?.id === t.id && 'opacity-40')}>
                    <div className="flex items-start gap-3">
                      <ScoreRing score={t.match_score} size={38} grosor={4} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/candidatos/${t.candidato_id}`} className="block truncate text-sm font-medium text-slate-900 hover:text-brand-700">{t.nombre}</Link>
                        <p className="text-xs text-slate-500">{t.experiencia_anios ?? 0} años exp. · {hace(t.creada_en)}</p>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      <Badge>{FUENTE[t.fuente] || t.fuente}</Badge>
                      {t.faltan_obligatorias > 0 && <Badge tono="rojo"><AlertTriangle className="h-3 w-3" />Faltan {t.faltan_obligatorias}</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {editable && <Portales vacanteId={id} abierto={portales} onCerrar={() => setPortales(false)} onImportado={recargar} />}

      <Modal abierto={!!descarte} onCerrar={() => setDescarte(null)} titulo={`Descartar a ${descarte?.nombre}`}>
        <p className="mb-3 text-sm text-slate-600">El motivo es interno: el candidato solo verá «Proceso finalizado» y, si está activado, recibirá un correo de rechazo amable.</p>
        <Campo label="Motivo del descarte">
          <textarea className="input" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. No cumple con la experiencia mínima en backend" />
        </Campo>
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setDescarte(null)}>Cancelar</button>
          <button className="btn-danger" disabled={!motivo.trim()} onClick={() => { mover(descarte, 'descartado', motivo); setDescarte(null) }}>Descartar</button>
        </div>
      </Modal>
    </div>
  )
}
