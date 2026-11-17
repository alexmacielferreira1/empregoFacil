import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Briefcase, LocateFixed, MapPin, Search } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Campo, Carregando, CursoCard, Erro, Interruptor, SelectCategoria, SelectLocal, VagaCard, VagaCompacta } from '../components'

function IlustracaoCurriculo() {
  return (
    <svg className="banner-ilustracao" viewBox="0 0 120 120" aria-hidden>
      <g stroke="#0d3d6b" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M86 14l5-8M96 22l9-4M98 34h8" fill="none" />
        <path d="M24 26l52-10 14 12 6 66-62 12z" fill="#fff" transform="rotate(-6 60 60)" />
        <path d="M38 46h34M38 58h38M38 70h30M38 82h22" fill="none" transform="rotate(-6 60 60)" />
      </g>
      <circle cx="88" cy="88" r="17" fill="#2b7bd4" stroke="#0d3d6b" strokeWidth="3.5" />
      <path d="M80 88l6 6 11-12" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function useDebounce(valor, ms = 350) {
  const [v, setV] = useState(valor)
  useEffect(() => { const t = setTimeout(() => setV(valor), ms); return () => clearTimeout(t) }, [valor, ms])
  return v
}

export function Inicio() {
  const { user } = useAuth()
  const [cv, setCv] = useState(undefined)
  const [vagas, setVagas] = useState(null)
  const [cursos, setCursos] = useState([])

  useEffect(() => {
    api('/api/candidato/curriculo').then(setCv).catch(() => setCv(null))
    api('/api/candidato/vagas').then((v) => setVagas(v.slice(0, 3))).catch(() => setVagas([]))
    api('/api/candidato/cursos-sugeridos').then((c) => setCursos(c.slice(0, 2))).catch(() => {})
  }, [])

  const banner = cv === undefined ? null : !cv
    ? { titulo: 'Monte seu currículo', texto: 'Responda algumas perguntas falando. A gente escreve o currículo para você.', botao: 'Começar agora', to: '/entrevista' }
    : !cv.confirmado
      ? { titulo: 'Confira seu currículo', texto: 'Ouça ou leia com calma e confirme se está tudo certo.', botao: 'Conferir currículo', to: '/curriculo' }
      : { titulo: 'Revise seu currículo', texto: 'Deixe seus dados atualizados para aumentar suas chances de conseguir uma vaga.', botao: 'Conferir currículo', to: '/curriculo' }

  return (
    <div>
      <h1>Olá, {user?.nome?.split(' ')[0]}!</h1>
      {banner && (
        <section className="banner">
          <div className="banner-texto">
            <h2>{banner.titulo}</h2>
            <p>{banner.texto}</p>
            <Link to={banner.to} className="botao">{banner.botao} <ArrowRight size={20} /></Link>
          </div>
          <IlustracaoCurriculo />
        </section>
      )}

      <div className="cabecalho-secao"><h2>Vagas perto de você</h2><Link to="/vagas">Ver todas</Link></div>
      {vagas === null ? <Carregando /> : vagas.length ? vagas.map((v) => <VagaCompacta key={v.id} vaga={v} />)
        : <p className="quieto">Nenhuma vaga aberta agora.</p>}

      {cursos.length > 0 && <>
        <div className="cabecalho-secao"><h2>Cursos para você</h2><Link to="/cursos">Ver todos</Link></div>
        {cursos.map((c) => <CursoCard key={c.id} curso={c} />)}
      </>}
    </div>
  )
}

export function Vagas() {
  const { user, meta } = useAuth()
  const [params] = useSearchParams()
  const vagaAberta = Number(params.get('vaga')) || null
  const ehCand = user?.role === 'candidato'
  const [f, setF] = useState({ categoria: '', com_treinamento: false, sem_experiencia: false, raio_km: '', bairro: '' })
  const [busca, setBusca] = useState('')
  const buscaAtrasada = useDebounce(busca)
  const [vagas, setVagas] = useState(null)
  const [temCv, setTemCv] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (!ehCand) return
    api('/api/candidato/curriculo').then((c) => setTemCv(!!c)).catch(() => {})
    api('/api/candidato/perfil').then((p) => p.bairro && setF((x) => ({ ...x, bairro: x.bairro || p.bairro }))).catch(() => {})
  }, [ehCand])

  useEffect(() => {
    setErro('')
    api(ehCand ? '/api/candidato/vagas' : '/api/vagas', { params: { ...f, busca: buscaAtrasada } })
      .then(setVagas).catch((e) => setErro(e.message))
  }, [JSON.stringify(f), buscaAtrasada, ehCand])

  useEffect(() => {
    if (vagaAberta && vagas) document.getElementById(`vaga-${vagaAberta}`)?.scrollIntoView({ block: 'center' })
  }, [vagaAberta, vagas])

  const set = (k, v) => setF({ ...f, [k]: v })
  const primeiraExemplo = vagas?.findIndex((v) => v.exemplo)

  return (
    <div>
      <h1>Encontre sua vaga</h1>
      <div className="form">
        <label className="seletor-local">
          <MapPin size={22} aria-hidden />
          <select value={f.bairro} onChange={(e) => set('bairro', e.target.value)} aria-label="Perto de onde">
            <option value="">{ehCand ? 'Perto de casa' : 'Qualquer lugar'}</option>
            {meta.locais.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </label>
        <div className="busca">
          <Search size={20} aria-hidden />
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Cargo ou palavra-chave" aria-label="Buscar vaga" />
        </div>
        <div className="duas-colunas">
          <SelectCategoria value={f.categoria} onChange={(v) => set('categoria', v)} />
          <select value={f.raio_km} onChange={(e) => set('raio_km', e.target.value)} aria-label="Distância">
            <option value="">Distância</option><option value="3">Até 3 km</option><option value="5">Até 5 km</option>
            <option value="10">Até 10 km</option><option value="20">Até 20 km</option>
          </select>
        </div>
        <div className="chips">
          <button type="button" className={`chip ${f.sem_experiencia ? 'ativa' : ''}`} aria-pressed={f.sem_experiencia} onClick={() => set('sem_experiencia', !f.sem_experiencia)}>Sem experiência</button>
          <button type="button" className={`chip ${f.com_treinamento ? 'ativa' : ''}`} aria-pressed={f.com_treinamento} onClick={() => set('com_treinamento', !f.com_treinamento)}>Com treinamento</button>
        </div>
      </div>

      {ehCand && !temCv && <p className="aviso" style={{ marginTop: '1rem' }}>Para se candidatar, <Link to="/entrevista">monte seu currículo</Link> primeiro. Leva uns 5 minutos.</p>}
      {!user && <p className="aviso" style={{ marginTop: '1rem' }}><Link to="/cadastro">Crie sua conta grátis</Link> para se candidatar.</p>}
      <Erro msg={erro} />
      {vagas === null ? <Carregando /> : vagas.length === 0 ? <p className="quieto" style={{ marginTop: '1rem' }}>Nenhuma vaga com esses filtros.</p>
        : vagas.map((v, i) => (
          <div key={v.id}>
            {i === primeiraExemplo && <p className="rotulo-secao">Vagas de exemplo</p>}
            <VagaCard vaga={v} podeCandidatar={ehCand && temCv} semConta={!user} abertaInicial={v.id === vagaAberta} />
          </div>
        ))}
    </div>
  )
}

export function Cursos() {
  const { user } = useAuth()
  const [f, setF] = useState({ categoria: '', gratuito: false, modalidade: '' })
  const [busca, setBusca] = useState('')
  const buscaAtrasada = useDebounce(busca)
  const [cursos, setCursos] = useState(null)
  const [perfil, setPerfil] = useState(null)

  useEffect(() => { if (user?.role === 'candidato') api('/api/candidato/perfil').then(setPerfil).catch(() => {}) }, [user])
  useEffect(() => {
    api('/api/cursos', { params: { ...f, busca: buscaAtrasada, lat: perfil?.lat, lng: perfil?.lng } }).then(setCursos).catch(() => setCursos([]))
  }, [JSON.stringify(f), buscaAtrasada, perfil])

  return (
    <div>
      <h1>Cursos</h1>
      <div className="form">
        <div className="busca">
          <Search size={20} aria-hidden />
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar curso" aria-label="Buscar curso" />
        </div>
        <div className="duas-colunas">
          <SelectCategoria value={f.categoria} onChange={(v) => setF({ ...f, categoria: v })} />
          <select value={f.modalidade} onChange={(e) => setF({ ...f, modalidade: e.target.value })} aria-label="Formato">
            <option value="">Formato</option><option value="presencial">Presencial</option><option value="online">Online</option>
          </select>
        </div>
        <Interruptor checked={f.gratuito} onChange={(v) => setF({ ...f, gratuito: v })}>Só grátis</Interruptor>
      </div>
      {cursos === null ? <Carregando /> : cursos.length === 0 ? <p className="quieto">Nenhum curso encontrado.</p>
        : cursos.map((c) => <CursoCard key={c.id} curso={c} />)}
    </div>
  )
}

const DISPONIBILIDADES = ['De segunda a sexta', 'Fins de semana', 'Qualquer dia', 'Só de manhã', 'Só à tarde', 'Só à noite']

export function Perfil() {
  const { user, sair } = useAuth()
  const nav = useNavigate()
  const [p, setP] = useState(null)
  const [nome, setNome] = useState(user?.nome || '')
  const [apps, setApps] = useState([])
  const [msg, setMsg] = useState('')
  const [erro, setErro] = useState('')

  useEffect(() => {
    api('/api/candidato/perfil').then(setP).catch((e) => setErro(e.message))
    api('/api/candidato/candidaturas').then(setApps).catch(() => {})
  }, [])

  async function salvar(e) {
    e.preventDefault(); setMsg(''); setErro('')
    try {
      const r = await api('/api/candidato/perfil', { method: 'PUT', body: { nome, bairro: p.bairro, disponibilidade: p.disponibilidade } })
      setP(r); setMsg('Alterações salvas.')
    } catch (e2) { setErro(e2.message) }
  }

  function usarLocalizacao() {
    setMsg(''); setErro('')
    if (!navigator.geolocation) return setErro('Seu celular não informou a localização.')
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const r = await api('/api/candidato/perfil', { method: 'PUT', body: { lat: pos.coords.latitude, lng: pos.coords.longitude } })
      setP(r); setMsg('Pronto! As distâncias agora são a partir de onde você está.')
    }, () => setErro('Não foi possível pegar sua localização. Permita o acesso no navegador.'))
  }

  const iniciais = (nome || user?.nome || '?').split(' ').filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase()
  const STATUS = { enviada: 'Enviada', vista: 'A empresa viu', entrevista: 'Chamado para entrevista', contratado: 'Contratado', recusada: 'Não seguiu' }
  const disp = p?.disponibilidade || ''
  const opcoesDisp = disp && !DISPONIBILIDADES.includes(disp) ? [disp, ...DISPONIBILIDADES] : DISPONIBILIDADES

  if (!p) return erro ? <Erro msg={erro} /> : <Carregando />
  return (
    <div>
      <h1>Meu perfil</h1>
      <div className="perfil-topo"><div className="avatar" aria-hidden>{iniciais}</div><b>{nome || user?.nome}</b></div>
      <form className="form" onSubmit={salvar}>
        <Campo label="Nome"><input value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" /></Campo>
        <div className="duas-colunas">
          <Campo label="Bairro"><SelectLocal value={p.bairro} onChange={(v) => setP({ ...p, bairro: v })} vazio="Escolha" /></Campo>
          <Campo label="Disponibilidade">
            <select value={disp} onChange={(e) => setP({ ...p, disponibilidade: e.target.value })}>
              <option value="">Escolha</option>
              {opcoesDisp.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Campo>
        </div>
        <button type="button" className="secundario largo" onClick={usarLocalizacao}><LocateFixed size={20} />Usar minha localização</button>
        <Erro msg={erro} />{msg && <p className="sucesso">{msg}</p>}
        <button className="grande">Salvar alterações</button>
      </form>

      <h2>Minhas candidaturas</h2>
      {apps.length === 0 ? (
        <div className="vazio-card">
          <Briefcase size={40} strokeWidth={1.6} aria-hidden />
          <p>Você ainda não se candidatou.</p>
          <Link to="/vagas">Ver vagas</Link>
        </div>
      ) : (
        <ul className="lista">{apps.map((a) => <li key={a.id}><b>{a.vaga}</b><br /><span className="quieto">{a.empresa} · {STATUS[a.status] || a.status}</span></li>)}</ul>
      )}
      <p className="centro" style={{ marginTop: '1.5rem' }}><button className="link" onClick={() => { sair(); nav('/') }}>Sair da conta</button></p>
    </div>
  )
}
