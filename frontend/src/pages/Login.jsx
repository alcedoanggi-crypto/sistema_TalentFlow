import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Sparkles, FileSearch, KanbanSquare, ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth'
import { Alerta, Spinner } from '../components/ui'

const DEMO = [
  ['admin@talentflow.demo', 'Admin'],
  ['reclutadora@talentflow.demo', 'Reclutadora'],
  ['carlos@talentflow.demo', 'Entrevistador'],
]

export default function Login() {
  const { usuario, login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('admin@talentflow.demo')
  const [password, setPassword] = useState('Demo1234!')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  if (usuario) return <Navigate to="/" replace />

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true); setError('')
    try { await login(email, password); nav('/') } catch (err) { setError(err.message) } finally { setEnviando(false) }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-gradient-to-br from-indigo-950 via-indigo-900 to-slate-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-brand-500 font-bold">T</div>
          <span className="text-lg font-semibold">TalentFlow</span>
        </div>
        <div>
          <h1 className="max-w-md text-4xl font-semibold leading-tight">Contrata mejor, con datos y con respeto por las personas.</h1>
          <ul className="mt-8 space-y-4 text-indigo-100/90">
            {[[FileSearch, 'Análisis automático de CV con spaCy y búsqueda full-text'],
              [Sparkles, 'Match candidato-vacante explicable: qué cumple y qué falta'],
              [KanbanSquare, 'Pipeline Kanban, entrevistas con .ics y pruebas técnicas autocalificadas'],
              [ShieldCheck, 'Consentimiento, retención limitada y derecho al olvido']].map(([I, t]) => (
              <li key={t} className="flex items-center gap-3"><I className="h-5 w-5 text-indigo-300" />{t}</li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-indigo-200/60">Proyecto de portafolio · Python · FastAPI · PostgreSQL · React</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={enviar} className="w-full max-w-sm space-y-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Iniciar sesión</h2>
            <p className="mt-1 text-sm text-slate-500">Accede al panel de reclutamiento.</p>
          </div>
          <Alerta>{error}</Alerta>
          <label className="block"><span className="label">Correo</span>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label className="block"><span className="label">Contraseña</span>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          <button className="btn-primary w-full" disabled={enviando}>{enviando ? <Spinner className="h-4 w-4 text-white" /> : 'Entrar'}</button>
          <div className="rounded-lg border border-dashed border-slate-300 p-3">
            <p className="mb-2 text-xs font-medium text-slate-500">Cuentas demo · contraseña <code>Demo1234!</code></p>
            <div className="flex flex-wrap gap-1.5">
              {DEMO.map(([e, r]) => (
                <button type="button" key={e} onClick={() => setEmail(e)}
                  className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700 hover:bg-brand-50 hover:text-brand-700">{r}</button>
              ))}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
