import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider, useAuth } from './auth'
import Layout from './components/Layout'
import { Cargando } from './components/ui'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Vacantes from './pages/Vacantes'
import VacanteForm from './pages/VacanteForm'
import Pipeline from './pages/Pipeline'
import Candidatos from './pages/Candidatos'
import CandidatoDetalle from './pages/CandidatoDetalle'
import Entrevistas from './pages/Entrevistas'
import Pruebas from './pages/Pruebas'
import Comunicacion from './pages/Comunicacion'
import Habilidades from './pages/Habilidades'
import Privacidad from './pages/Privacidad'
import MiBusqueda from './pages/MiBusqueda'
import Empleos from './pages/publico/Empleos'
import VacantePublica from './pages/publico/VacantePublica'
import Portal from './pages/publico/Portal'
import PruebaCandidato from './pages/publico/PruebaCandidato'

function Protegida({ children }) {
  const { usuario, cargando } = useAuth()
  if (cargando) return <Cargando />
  return usuario ? children : <Navigate to="/login" replace />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/empleos/:slug" element={<Empleos />} />
          <Route path="/empleos/:slug/:vslug" element={<VacantePublica />} />
          <Route path="/portal/:token" element={<Portal />} />
          <Route path="/prueba/:token" element={<PruebaCandidato />} />
          <Route element={<Protegida><Layout /></Protegida>}>
            <Route index element={<Dashboard />} />
            <Route path="vacantes" element={<Vacantes />} />
            <Route path="vacantes/nueva" element={<VacanteForm />} />
            <Route path="vacantes/:id/editar" element={<VacanteForm />} />
            <Route path="vacantes/:id" element={<Pipeline />} />
            <Route path="candidatos" element={<Candidatos />} />
            <Route path="candidatos/:id" element={<CandidatoDetalle />} />
            <Route path="entrevistas" element={<Entrevistas />} />
            <Route path="pruebas" element={<Pruebas />} />
            <Route path="comunicacion" element={<Comunicacion />} />
            <Route path="habilidades" element={<Habilidades />} />
            <Route path="privacidad" element={<Privacidad />} />
            <Route path="mi-busqueda" element={<MiBusqueda />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
