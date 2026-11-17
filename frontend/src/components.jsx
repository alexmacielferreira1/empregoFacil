import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  Award, BarChart3, Briefcase, ChefHat, ChevronRight, Clock, FileText, GraduationCap, HardHat, HeartHandshake,
  House, Laptop, LogOut, MapPin, Plus, Scissors, ShoppingCart, Sparkles, SprayCan, Sprout, Store, User, Users, Wrench,
  Check, BookOpen,
} from 'lucide-react'
import { api, brl } from './api'
import { useAuth } from './auth'

// ---------- ícones por área ----------
const ICONE_AREA = {
  limpeza: SprayCan, construcao: HardHat, costura: Scissors, cozinha: ChefHat, cuidados: HeartHandshake,
  comercio: Store, logistica: ShoppingCart, beleza: Sparkles, manutencao: Wrench, jardinagem: Sprout,
  administrativo: Laptop, outros: Briefcase,
}

export function IconeArea({ categoria, tamanho = 30 }) {
  const Icone = ICONE_AREA[categoria] || Briefcase
  return <div className="icone-area" aria-hidden><Icone size={tamanho} strokeWidth={1.8} /></div>
}

// ---------- estrutura ----------
const MENUS = {
  candidato: [['/inicio', House, 'Início'], ['/curriculo', FileText, 'Currículo'], ['/vagas', Briefcase, 'Vagas'], ['/cursos', GraduationCap, 'Cursos'], ['/perfil', User, 'Perfil']],
  empresa: [['/empresa', Briefcase, 'Vagas'], ['/empresa/nova', Plus, 'Nova vaga'], ['/cursos', GraduationCap, 'Cursos']],
  parceiro: [['/parceiro', Users, 'Pessoas'], ['/vagas', Briefcase, 'Vagas'], ['/cursos', GraduationCap, 'Cursos']],
  admin: [['/admin', BarChart3, 'Painel'], ['/admin/cursos', BookOpen, 'Cursos'], ['/vagas', Briefcase, 'Vagas']],
}

export function Layout({ children }) {
  const { user, sair } = useAuth()
  const { pathname } = useLocation()
  const menu = user ? MENUS[user.role] || [] : []
  const ehCandidato = user?.role === 'candidato'
  // "Currículo" fica ativo também durante a entrevista
  const ativo = (to) => pathname === to || (to === '/curriculo' && pathname === '/entrevista')

  return (
    <div className={`app ${menu.length ? 'com-menu' : ''}`}>
      <header className="topo">
        <Link to="/" className="marca" aria-label="Emprego Fácil, início"><img src="/logo.svg" alt="Emprego Fácil" width="166" height="34" /></Link>
        {!user && <Link to="/entrar" className="link-entrar">Entrar</Link>}
        {ehCandidato && (pathname === '/perfil'
          ? <button className="topo-acao" onClick={sair} aria-label="Sair da conta" title="Sair"><LogOut size={24} /></button>
          : <Link to="/perfil" className="topo-acao" aria-label="Meu bairro e perfil"><MapPin size={26} /></Link>)}
        {user && !ehCandidato && <button className="topo-acao" onClick={sair} aria-label="Sair da conta" title="Sair"><LogOut size={24} /></button>}
      </header>
      <main className="conteudo">{children}</main>
      {menu.length > 0 && (
        <nav className="menu-inferior" aria-label="Menu principal">
          {menu.map(([to, Icone, label]) => (
            <NavLink key={to} to={to} end className={() => (ativo(to) ? 'active' : '')}>
              <Icone size={24} strokeWidth={ativo(to) ? 2.2 : 1.8} aria-hidden />{label}
            </NavLink>
          ))}
        </nav>
      )}
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

export const textoDistancia = (km) => (km == null ? null : km < 1 ? 'no seu bairro' : `${km.toLocaleString('pt-BR')} km`)

function Local({ bairro, cidade, km }) {
  const d = textoDistancia(km)
  return (
    <p className="linha-info"><MapPin size={18} aria-hidden />{bairro || cidade}{d ? ` · ${d}` : ''}</p>
  )
}

// ---------- vagas ----------
export function VagaCompacta({ vaga }) {
  return (
    <Link to={`/vagas?vaga=${vaga.id}`} className="card vaga-compacta">
      <IconeArea categoria={vaga.categoria} />
      <div className="vaga-corpo">
        <h3>{vaga.titulo}</h3>
        <Local bairro={vaga.bairro} cidade={vaga.cidade} km={vaga.distancia_km} />
        {vaga.salario && <p className="salario">{vaga.salario}</p>}
        <div className="selos">
          {!vaga.exige_experiencia && <Selo>Sem experiência</Selo>}
          {vaga.com_treinamento && <Selo tipo="destaque"><GraduationCap size={14} />Treinamos você</Selo>}
        </div>
      </div>
      <ChevronRight className="seta" size={24} aria-hidden />
    </Link>
  )
}

export function VagaCard({ vaga, podeCandidatar, onCandidatou, abertaInicial = false, semConta }) {
  const { nomeCategoria } = useAuth()
  const [aberta, setAberta] = useState(abertaInicial)
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
    <article className="card" id={`vaga-${vaga.id}`}>
      <div className="vaga">
        <IconeArea categoria={vaga.categoria} />
        <div className="vaga-corpo">
          <h3>{vaga.titulo}</h3>
          <Local bairro={vaga.bairro} cidade={vaga.cidade} km={vaga.distancia_km} />
          {vaga.salario && <p className="salario">{vaga.salario}</p>}
          {vaga.horario && <p className="linha-info"><Clock size={18} aria-hidden />{vaga.horario}</p>}
          <div className="selos">
            {vaga.combina && <Selo tipo="bom"><Check size={14} />Combina com você</Selo>}
            {vaga.com_treinamento && <Selo tipo="destaque"><GraduationCap size={14} />Treinamos você{vaga.tipo_treinamento === 'antes' ? ' antes' : ''}</Selo>}
            {!vaga.exige_experiencia && <Selo>Sem experiência</Selo>}
          </div>
        </div>
      </div>
      {aberta && (
        <div className="detalhe">
          <p>{vaga.descricao}</p>
          <p className="quieto">{vaga.empresa} · {nomeCategoria(vaga.categoria)}</p>
          {vaga.vantagens?.length > 0 && <p><b>Vantagens:</b> {vaga.vantagens.join(' · ')}</p>}
          {vaga.com_treinamento && vaga.descricao_treinamento && <p><b>Treinamento:</b> {vaga.descricao_treinamento}</p>}
          {vaga.curso && <p><b>Curso ligado:</b> {vaga.curso.titulo} ({brl(vaga.curso.preco)})</p>}
        </div>
      )}
      <div className="vaga-acoes">
        {podeCandidatar && (estado === 'ok'
          ? <span className="sucesso"><Check size={20} />Candidatura enviada</span>
          : <button onClick={candidatar} disabled={estado === 'enviando'}>{estado === 'enviando' ? 'Enviando…' : 'Quero esta vaga'}</button>)}
        {semConta && <Link className="botao" to="/cadastro">Quero esta vaga</Link>}
        <button className="link" onClick={() => setAberta(!aberta)}>{aberta ? 'Fechar detalhes' : 'Ver detalhes'}</button>
      </div>
      <Erro msg={erro} />
    </article>
  )
}

// ---------- cursos ----------
// Foto: imagem_url do curso, senão /img/cursos/<area>.jpg (coloque as imagens em frontend/public/img/cursos),
// senão um fundo amarelo com o ícone da área.
function FotoCurso({ curso }) {
  const Icone = ICONE_AREA[curso.categoria] || GraduationCap
  const [src, setSrc] = useState(curso.imagem_url || `/img/cursos/${curso.categoria}.jpg`)
  const [falhou, setFalhou] = useState(false)
  return (
    <div className="curso-foto">
      {falhou ? <Icone size={48} strokeWidth={1.5} aria-hidden /> : (
        <img src={src} alt="" loading="lazy" onError={() => {
          if (curso.imagem_url && src === curso.imagem_url) setSrc(`/img/cursos/${curso.categoria}.jpg`)
          else setFalhou(true)
        }} />
      )}
    </div>
  )
}

export function CursoCard({ curso }) {
  const { nomeCategoria } = useAuth()
  const [aberto, setAberto] = useState(false)
  const online = curso.modalidade === 'online'
  const d = textoDistancia(curso.distancia_km)
  return (
    <article className="card curso">
      <FotoCurso curso={curso} />
      <div className="curso-corpo">
        <div className="card-topo">
          <h3>{curso.titulo}</h3>
          <span className={`selo ${curso.preco === 0 ? 'gratis' : 'destaque'}`}>{brl(curso.preco)}</span>
        </div>
        <p className="linha-info">
          {online ? <Laptop size={18} aria-hidden /> : <MapPin size={18} aria-hidden />}
          {online ? 'Online' : 'Presencial'}
          {curso.carga_horaria ? ` · ${curso.carga_horaria} h` : ''}
        </p>
        {!online && curso.bairro && <p className="linha-info quieto">{curso.bairro}{d ? ` · ${d}` : ''}</p>}
        {curso.certificado && <p className="linha-info"><Award size={18} aria-hidden />Certificado</p>}
        {curso.abre_vaga && <div className="selos"><Selo tipo="destaque"><Briefcase size={14} />Abre porta para vaga</Selo></div>}
        {aberto && (
          <div className="detalhe">
            <p className="quieto">{curso.ofertante} · {nomeCategoria(curso.categoria)}</p>
            {curso.horario && <p className="linha-info"><Clock size={18} aria-hidden />{curso.horario}</p>}
            {curso.descricao && <p>{curso.descricao}</p>}
            {curso.contato && <p>Contato: {curso.contato}</p>}
          </div>
        )}
        <div className="vaga-acoes">
          {curso.link && <a className="botao" href={curso.link} target="_blank" rel="noreferrer">Inscrever-se</a>}
          <button className="link" onClick={() => setAberto(!aberto)}>{aberto ? 'Fechar detalhes' : 'Ver detalhes'}</button>
        </div>
      </div>
    </article>
  )
}

// ---------- formulário ----------
export function Campo({ label, children, dica }) {
  return (
    <label className="campo">
      <span>{label}</span>
      {children}
      {dica && <small className="quieto">{dica}</small>}
    </label>
  )
}

export function Interruptor({ checked, onChange, children }) {
  return (
    <label className="interruptor">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="trilho" aria-hidden />
      {children}
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

export function SelectCategoria({ value, onChange, vazio = 'Área' }) {
  const { meta } = useAuth()
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)} aria-label="Área">
      <option value="">{vazio}</option>
      {meta.categorias.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
    </select>
  )
}
