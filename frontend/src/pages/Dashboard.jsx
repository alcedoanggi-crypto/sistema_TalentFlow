import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { Clock, Users, UserCheck, Target } from 'lucide-react'
import { api } from '../api'
import { Cargando, Encabezado, Kpi, useCarga, Alerta, Badge } from '../components/ui'

const Tip = ({ active, payload, label }) => active && payload?.length ? (
  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg">
    <p className="mb-1 font-medium text-slate-700">{label}</p>
    {payload.map((p) => <p key={p.dataKey} style={{ color: p.color || p.payload.color }}>{p.name}: <b>{p.value}</b></p>)}
  </div>) : null

export default function Dashboard() {
  const [vacante, setVacante] = useState('')
  const [dias, setDias] = useState(180)
  const [vacantes] = useCarga(() => api.get('/vacantes'), [])
  const [d, cargando, error] = useCarga(() => api.get(`/dashboard?dias=${dias}${vacante ? `&vacante_id=${vacante}` : ''}`), [vacante, dias])

  return (
    <div>
      <Encabezado titulo="Dashboard de reclutamiento" subtitulo="Métricas del embudo calculadas en PostgreSQL a partir del historial de etapas.">
        <select className="input w-auto" value={vacante} onChange={(e) => setVacante(e.target.value)}>
          <option value="">Todas las vacantes</option>
          {vacantes?.map((v) => <option key={v.id} value={v.id}>{v.titulo}</option>)}
        </select>
        <select className="input w-auto" value={dias} onChange={(e) => setDias(+e.target.value)}>
          <option value={30}>Últimos 30 días</option><option value={90}>Últimos 90 días</option>
          <option value={180}>Últimos 6 meses</option><option value={365}>Último año</option>
        </select>
      </Encabezado>
      <Alerta>{error}</Alerta>
      {cargando && !d ? <Cargando /> : d && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi titulo="Tiempo promedio de contratación" valor={d.kpis.tiempo_contratacion} sufijo="días" icono={Clock}
              nota={d.kpis.tiempo_mediana != null ? `Mediana: ${d.kpis.tiempo_mediana} días` : 'Aún sin contrataciones'} />
            <Kpi titulo="Postulaciones" valor={d.kpis.total} icono={Users} nota={`${d.kpis.activas} en proceso activo`} />
            <Kpi titulo="Contrataciones" valor={d.kpis.contratados} icono={UserCheck} tono="verde" nota={`Tasa global: ${d.kpis.tasa_contratacion}%`} />
            <Kpi titulo="Match promedio" valor={d.kpis.match_promedio} sufijo="/100" icono={Target} tono="ambar" nota="Compatibilidad CV ↔ requisitos" />
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="card p-5 lg:col-span-3">
              <h3 className="font-semibold text-slate-900">Embudo de conversión</h3>
              <p className="mb-4 text-xs text-slate-500">Postulaciones que alcanzaron cada etapa y % que pasa a la siguiente.</p>
              <div className="space-y-2.5">
                {d.embudo.map((e) => (
                  <div key={e.codigo} className="flex items-center gap-3">
                    <span className="w-36 shrink-0 text-sm text-slate-600">{e.nombre}</span>
                    <div className="h-8 flex-1 rounded-md bg-slate-100">
                      <div className="flex h-8 items-center rounded-md px-2 text-xs font-semibold text-white transition-all duration-700"
                        style={{ width: `${Math.max(e.porcentaje, 6)}%`, background: e.color }}>{e.alcanzaron}</div>
                    </div>
                    <span className="w-20 shrink-0 text-right text-xs tabular-nums text-slate-500">
                      {e.conversion != null ? <>→ <b className="text-slate-700">{e.conversion}%</b></> : '100%'}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card p-5 lg:col-span-2">
              <h3 className="font-semibold text-slate-900">Candidatos por etapa (hoy)</h3>
              <p className="mb-2 text-xs text-slate-500">Distribución actual del pipeline.</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={d.por_etapa} layout="vertical" margin={{ left: 10 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="nombre" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip content={<Tip />} cursor={{ fill: '#f1f5f9' }} />
                  <Bar dataKey="total" name="Candidatos" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                    {d.por_etapa.map((e) => <Cell key={e.codigo} fill={e.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="card overflow-hidden">
              <div className="p-5 pb-3">
                <h3 className="font-semibold text-slate-900">Fuentes de reclutamiento más efectivas</h3>
                <p className="text-xs text-slate-500">Ordenadas por contrataciones; la tasa de entrevista mide la calidad del canal.</p>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs text-slate-500">
                  <tr><th className="px-5 py-2 font-medium">Fuente</th><th className="px-2 py-2 text-right font-medium">Postul.</th>
                    <th className="px-2 py-2 text-right font-medium">% entrevista</th><th className="px-2 py-2 text-right font-medium">Contrat.</th>
                    <th className="px-5 py-2 text-right font-medium">Match</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {d.fuentes.map((f, i) => (
                    <tr key={f.fuente}>
                      <td className="px-5 py-2.5 font-medium text-slate-700">{f.nombre} {i === 0 && f.contratados > 0 && <Badge tono="verde">Mejor canal</Badge>}</td>
                      <td className="px-2 text-right tabular-nums">{f.postulaciones}</td>
                      <td className="px-2 text-right">
                        <div className="ml-auto flex w-24 items-center gap-2"><div className="h-1.5 flex-1 rounded bg-slate-100">
                          <div className="h-1.5 rounded bg-brand-500" style={{ width: `${f.tasa_entrevista}%` }} /></div>
                          <span className="w-8 text-xs tabular-nums">{f.tasa_entrevista}%</span></div>
                      </td>
                      <td className="px-2 text-right font-semibold tabular-nums text-emerald-700">{f.contratados}</td>
                      <td className="px-5 text-right tabular-nums text-slate-500">{f.match_promedio}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900">Postulaciones por semana</h3>
              <p className="mb-2 text-xs text-slate-500">Volumen de entrada y contrataciones de esas cohortes.</p>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={d.tendencia}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="semana" tick={{ fontSize: 11 }} tickFormatter={(s) => s.slice(5)} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip content={<Tip />} /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="postulaciones" name="Postulaciones" stroke="#6366f1" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="contratados" name="Contratados" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="p-5 pb-3"><h3 className="font-semibold text-slate-900">Rendimiento por vacante</h3></div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>
                <th className="px-5 py-2 font-medium">Vacante</th><th className="px-2 font-medium">Estado</th>
                <th className="px-2 text-right font-medium">Postulaciones</th><th className="px-2 text-right font-medium">Match prom.</th>
                <th className="px-2 text-right font-medium">Días abierta</th><th className="px-5 text-right font-medium">Días a contratación</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {d.vacantes.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50">
                    <td className="px-5 py-2.5"><Link to={`/vacantes/${v.id}`} className="font-medium text-brand-700 hover:underline">{v.titulo}</Link></td>
                    <td className="px-2"><Badge tono={v.estado === 'publicada' ? 'verde' : 'gris'}>{v.estado}</Badge></td>
                    <td className="px-2 text-right tabular-nums">{v.postulaciones}</td>
                    <td className="px-2 text-right tabular-nums">{v.match_promedio ?? '—'}</td>
                    <td className="px-2 text-right tabular-nums">{v.dias_abierta ?? '—'}</td>
                    <td className="px-5 text-right tabular-nums">{v.dias_contratacion ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
