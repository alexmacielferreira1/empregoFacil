import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, homeDe, useAuth } from './auth'
import { Layout } from './components'
import Curriculo, { EnviarCurriculo } from './pages/Curriculo'
import { Cursos, Inicio, Perfil, Vagas } from './pages/Candidato'
import { Candidatos, EmpresaVagas, VagaForm } from './pages/Empresa'
import Entrevista from './pages/Entrevista'
import { Admin, AdminCursos, Parceiro } from './pages/Gestao'
import { Cadastro, Entrar, Home, Recuperar } from './pages/Publico'
import './styles.css'

function Protegida({ roles, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/entrar" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={homeDe(user.role)} replace />
  return children
}

function Raiz() {
  const { user } = useAuth()
  return user ? <Navigate to={homeDe(user.role)} replace /> : <Home />
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Raiz />} />
        <Route path="/entrar" element={<Entrar />} />
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/recuperar" element={<Recuperar />} />
        <Route path="/vagas" element={<Vagas />} />
        <Route path="/cursos" element={<Cursos />} />

        <Route path="/inicio" element={<Protegida roles={['candidato']}><Inicio /></Protegida>} />
        <Route path="/entrevista" element={<Protegida roles={['candidato']}><Entrevista /></Protegida>} />
        <Route path="/curriculo" element={<Protegida roles={['candidato']}><Curriculo /></Protegida>} />
        <Route path="/curriculo/enviar" element={<Protegida roles={['candidato']}><EnviarCurriculo /></Protegida>} />
        <Route path="/perfil" element={<Protegida roles={['candidato']}><Perfil /></Protegida>} />

        <Route path="/empresa" element={<Protegida roles={['empresa']}><EmpresaVagas /></Protegida>} />
        <Route path="/empresa/nova" element={<Protegida roles={['empresa']}><VagaForm /></Protegida>} />
        <Route path="/empresa/vagas/:id" element={<Protegida roles={['empresa']}><Candidatos /></Protegida>} />
        <Route path="/empresa/vagas/:id/editar" element={<Protegida roles={['empresa']}><VagaForm /></Protegida>} />

        <Route path="/parceiro" element={<Protegida roles={['parceiro', 'admin']}><Parceiro /></Protegida>} />
        <Route path="/admin" element={<Protegida roles={['admin']}><Admin /></Protegida>} />
        <Route path="/admin/cursos" element={<Protegida roles={['admin']}><AdminCursos /></Protegida>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider><App /></AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
