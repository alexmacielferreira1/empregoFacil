import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { api, brl } from './api'
import { homeDe, useAuth } from './auth'

const MENUS = {
  candidato: [['/inicio', '🏠', 'Início'], ['/entrevista', '🎤', 'Currículo'], ['/vagas', '💼', 'Vagas'], ['/cursos', '📚', 'Cursos'], ['/perfil', '👤', 'Perfil']],
  empresa: [['/empresa', '💼', 'Minhas vagas'], ['/empresa/nova', '➕', 'Nova vaga'], ['/cursos', '📚', 'Cursos']],
  parceiro: [['/parceiro', '🤝', 'Pessoas'], ['/cursos', '📚', 'Cursos'], ['/vagas', '💼', 'Vagas']],
  admin: [['/admin', '📊', 'Painel'], ['/admin/cursos', '📚', 'Cursos'], ['/vagas', '💼', 'Vagas']],
}

export function Layout({ children }) {
  const { user, sair } = useAuth()
  const nav = useNavigate()
  const menu = user ? MENUS[user.role] || [] : []
  return (
    <div className="app">
      <header className="topo">
        <Link to={user ? homeDe(user.role) : '/'} className="marca"><img src="/icon.svg" alt="" /> emprego<b>Facil</b></Link>
        {user ? (
          <button className="link" onClick={() => { sair(); nav('/') }}>Sair</button>
        ) : (
          <Link to="/entrar" className="link">Entrar</Link>
        )}
      </header>
      {menu.length > 0 && (
        <nav className="menu">
          {menu.map(([to, ic, label]) => (
            <NavLink key={to} to={to} end><span aria-hidden>{ic}</span>{label}</NavLink>
          ))}
        </nav>
      )}
      <main className="conteudo">{children}</main>
    </div>
  )
}

export function Erro({ msg }) {
  return msg ? <p className="erro" role="alert">{msg}</p> : null
}

export function Carregando() {
  return <p className="quieto">Carregando…</p>
}

export function Selo({ children, tipo = '' }) {
  return <span className={`selo ${tipo}`}>{children}</span>
}

export function VagaCard({ vaga, podeCandidatar, onCandidatou }) {
  const { nomeCategoria } = useAuth()
  const [aberta, setAberta] = useState(false)
  const [estado, setEstado] = useState(vaga.ja_candidatou ? 'ok' : '')
  const [erro, setErro] = useState('')

  async function candidatar() {
    setErro(''); setEstado('enviando')
    try {
      await api(`/api/vagas/${vaga.id}/candidatar`, { method: 'POST', body: {} })
      setEstado('ok'); onCandidatou?.()
    } catch (e) { setErro(e.message); setEstado('') }
  }

  return (
    <article className="card">
      <div className="card-topo">
        <h3>{vaga.titulo}</h3>
        {vaga.distancia_km != null && <span className="distancia">📍 {vaga.distancia_km < 1 ? "No seu bairro" : `${vaga.distancia_km} km`}</span>}
      </div>
      <p className="quieto">{vaga.empresa} · {vaga.bairro || vaga.cidade}</p>
      <div className="selos">
        {vaga.combina && <Selo tipo="bom">Combina com você</Selo>}
        {vaga.com_treinamento && <Selo tipo="destaque">🎓 Treinamos você{vaga.tipo_treinamento === 'antes' ? ' (antes)' : ''}</Selo>}
        {!vaga.exige_experiencia && <Selo>Sem experiência</Selo>}
        {vaga.exemplo && <Selo tipo="aviso">Exemplo</Selo>}
      </div>
      {vaga.salario && <p><b>{vaga.salario}</b>{vaga.horario ? ` · ${vaga.horario}` : ''}</p>}
      {aberta && (
        <div className="detalhe">
          <p>{vaga.descricao}</p>
          <p className="quieto">Área: {nomeCategoria(vaga.categoria)}</p>
          {vaga.vantagens?.length > 0 && <p>✅ {vaga.vantagens.join(' · ')}</p>}
          {vaga.com_treinamento && vaga.descricao_treinamento && <p>🎓 {vaga.descricao_treinamento}</p>}
          {vaga.curso && <p>📚 Curso ligado: <b>{vaga.curso.titulo}</b> — {brl(vaga.curso.preco)}</p>}
        </div>
      )}
      <div className="acoes">
        <button className="secundario" onClick={() => setAberta(!aberta)}>{aberta ? 'Menos' : 'Ver mais'}</button>
        {podeCandidatar && (
          estado === 'ok'
            ? <span className="sucesso">✔ Candidatura enviada</span>
            : <button onClick={candidatar} disabled={estado === 'enviando'}>{estado === 'enviando' ? 'Enviando…' : 'Quero esta vaga'}</button>
        )}
      </div>
      <Erro msg={erro} />
    </article>
  )
}

export function CursoCard({ curso }) {
  const { nomeCategoria } = useAuth()
  return (
    <article className="card">
      <div className="card-topo">
        <h3>{curso.titulo}</h3>
        <span className={`preco ${curso.preco === 0 ? 'gratis' : ''}`}>{brl(curso.preco)}</span>
      </div>
      <p className="quieto">{curso.ofertante}</p>
      <div className="selos">
        <Selo>{curso.modalidade === 'online' ? '💻 Online' : `📍 ${curso.bairro || curso.cidade || 'Presencial'}`}</Selo>
        {curso.distancia_km != null && <Selo>{curso.distancia_km} km</Selo>}
        {curso.carga_horaria && <Selo>{curso.carga_horaria}h</Selo>}
        {curso.certificado && <Selo>Certificado</Selo>}
        {curso.abre_vaga && <Selo tipo="destaque">Abre porta para vaga</Selo>}
        {curso.exemplo && <Selo tipo="aviso">Exemplo</Selo>}
      </div>
      <p className="quieto">{nomeCategoria(curso.categoria)}{curso.horario ? ` · ${curso.horario}` : ''}</p>
      {curso.descricao && <p>{curso.descricao}</p>}
      {(curso.link || curso.contato) && (
        <p>{curso.link && <a href={curso.link} target="_blank" rel="noreferrer">Inscrever-se</a>}{curso.contato ? ` · ${curso.contato}` : ''}</p>
      )}
    </article>
  )
}

export function Campo({ label, children, dica }) {
  return (
    <label className="campo">
      <span>{label}</span>
      {children}
      {dica && <small className="quieto">{dica}</small>}
    </label>
  )
}

export function SelectLocal({ value, onChange, vazio = 'Escolha seu bairro ou cidade' }) {
  const { meta } = useAuth()
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
      <option value="">{vazio}</option>
      {meta.locais.map((l) => <option key={l} value={l}>{l}</option>)}
    </select>
  )
}

export function SelectCategoria({ value, onChange, vazio = 'Todas as áreas' }) {
  const { meta } = useAuth()
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
      <option value="">{vazio}</option>
      {meta.categorias.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
    </select>
  )
}
