import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Campo, Carregando, CursoCard, Erro, SelectCategoria, SelectLocal, VagaCard } from '../components'

export function Inicio() {
  const { user } = useAuth()
  const [cv, setCv] = useState(undefined)
  const [vagas, setVagas] = useState([])
  const [cursos, setCursos] = useState([])

  useEffect(() => {
    api('/api/candidato/curriculo').then(setCv).catch(() => setCv(null))
    api('/api/candidato/vagas').then((v) => setVagas(v.slice(0, 3))).catch(() => {})
    api('/api/candidato/cursos-sugeridos').then((c) => setCursos(c.slice(0, 3))).catch(() => {})
  }, [])

  return (
    <div>
      <h1>Olá, {user?.nome?.split(' ')[0]}!</h1>
      {cv === undefined ? <Carregando /> : !cv ? (
        <div className="destaque-box">
          <h2>Passo 1: seu currículo</h2>
          <p>Responda algumas perguntas falando. A gente escreve o currículo para você.</p>
          <Link to="/entrevista" className="botao grande">🎤 Montar meu currículo</Link>
        </div>
      ) : (
        <div className="destaque-box ok">
          <p>✔ Seu currículo está pronto{cv.confirmado ? '' : ' (falta você conferir)'}.</p>
          <Link to="/curriculo" className="botao secundario">Ver currículo</Link>
        </div>
      )}
      <h2>Vagas perto de você</h2>
      {vagas.length ? vagas.map((v) => <VagaCard key={v.id} vaga={v} podeCandidatar={!!cv} />) : <p className="quieto">Nenhuma vaga aberta agora.</p>}
      <Link to="/vagas">Ver todas as vagas →</Link>
      <h2>Cursos para você</h2>
      {cursos.map((c) => <CursoCard key={c.id} curso={c} />)}
      <Link to="/cursos">Ver todos os cursos →</Link>
    </div>
  )
}

export function Vagas() {
  const { user } = useAuth()
  const ehCand = user?.role === 'candidato'
  const [f, setF] = useState({ categoria: '', com_treinamento: false, sem_experiencia: false, raio_km: '', bairro: '' })
  const [vagas, setVagas] = useState(null)
  const [temCv, setTemCv] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => { if (ehCand) api('/api/candidato/curriculo').then((c) => setTemCv(!!c)).catch(() => {}) }, [ehCand])
  useEffect(() => {
    setErro('')
    api(ehCand ? '/api/candidato/vagas' : '/api/vagas', { params: f }).then(setVagas).catch((e) => setErro(e.message))
  }, [JSON.stringify(f), ehCand])

  return (
    <div>
      <h1>Vagas</h1>
      <div className="filtros">
        <SelectCategoria value={f.categoria} onChange={(v) => setF({ ...f, categoria: v })} />
        {!ehCand && <SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} vazio="Perto de onde?" />}
        <select value={f.raio_km} onChange={(e) => setF({ ...f, raio_km: e.target.value })}>
          <option value="">Qualquer distância</option><option value="3">Até 3 km</option><option value="5">Até 5 km</option><option value="10">Até 10 km</option><option value="20">Até 20 km</option>
        </select>
        <label className="check"><input type="checkbox" checked={f.com_treinamento} onChange={(e) => setF({ ...f, com_treinamento: e.target.checked })} /> Treinam você</label>
        <label className="check"><input type="checkbox" checked={f.sem_experiencia} onChange={(e) => setF({ ...f, sem_experiencia: e.target.checked })} /> Sem experiência</label>
      </div>
      {ehCand && !temCv && <p className="aviso">Para se candidatar, <Link to="/entrevista">monte seu currículo</Link> primeiro.</p>}
      {!user && <p className="aviso"><Link to="/cadastro">Crie sua conta</Link> para se candidatar.</p>}
      <Erro msg={erro} />
      {vagas === null ? <Carregando /> : vagas.length === 0 ? <p className="quieto">Nenhuma vaga com esses filtros.</p>
        : vagas.map((v) => <VagaCard key={v.id} vaga={v} podeCandidatar={ehCand && temCv} />)}
    </div>
  )
}

export function Cursos() {
  const { user } = useAuth()
  const [f, setF] = useState({ categoria: '', gratuito: false, modalidade: '', busca: '', bairro: '' })
  const [cursos, setCursos] = useState(null)
  const [perfil, setPerfil] = useState(null)

  useEffect(() => { if (user?.role === 'candidato') api('/api/candidato/perfil').then(setPerfil).catch(() => {}) }, [user])
  useEffect(() => {
    const params = { ...f, lat: perfil?.lat, lng: perfil?.lng }
    api('/api/cursos', { params }).then(setCursos).catch(() => setCursos([]))
  }, [JSON.stringify(f), perfil])

  return (
    <div>
      <h1>Cursos</h1>
      <div className="filtros">
        <input placeholder="Buscar: costura, azulejo, cozinha…" value={f.busca} onChange={(e) => setF({ ...f, busca: e.target.value })} />
        <SelectCategoria value={f.categoria} onChange={(v) => setF({ ...f, categoria: v })} />
        <select value={f.modalidade} onChange={(e) => setF({ ...f, modalidade: e.target.value })}>
          <option value="">Presencial ou online</option><option value="presencial">Presencial</option><option value="online">Online</option>
        </select>
        {!perfil && <SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} vazio="Perto de onde?" />}
        <label className="check"><input type="checkbox" checked={f.gratuito} onChange={(e) => setF({ ...f, gratuito: e.target.checked })} /> Só grátis</label>
      </div>
      {cursos === null ? <Carregando /> : cursos.length === 0 ? <p className="quieto">Nenhum curso encontrado.</p> : cursos.map((c) => <CursoCard key={c.id} curso={c} />)}
    </div>
  )
}

export function Perfil() {
  const { user } = useAuth()
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
      setP(r); setMsg('Salvo!')
    } catch (e2) { setErro(e2.message) }
  }

  function usarLocalizacao() {
    if (!navigator.geolocation) return setErro('Seu celular não informou a localização.')
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const r = await api('/api/candidato/perfil', { method: 'PUT', body: { lat: pos.coords.latitude, lng: pos.coords.longitude } })
      setP(r); setMsg('Localização atualizada. As distâncias agora são a partir de onde você está.')
    }, () => setErro('Não foi possível pegar sua localização.'))
  }

  const STATUS = { enviada: 'Enviada', vista: 'A empresa viu', entrevista: '📞 Chamado para entrevista', contratado: '🎉 Contratado', recusada: 'Não seguiu' }
  if (!p) return erro ? <Erro msg={erro} /> : <Carregando />
  return (
    <div>
      <h1>Meu perfil</h1>
      <form className="form" onSubmit={salvar}>
        <Campo label="Nome"><input value={nome} onChange={(e) => setNome(e.target.value)} /></Campo>
        <Campo label="Onde você mora"><SelectLocal value={p.bairro} onChange={(v) => setP({ ...p, bairro: v })} /></Campo>
        <button type="button" className="link" onClick={usarLocalizacao}>📍 Usar minha localização atual</button>
        <Campo label="Dias e horários que pode trabalhar"><input value={p.disponibilidade || ''} onChange={(e) => setP({ ...p, disponibilidade: e.target.value })} /></Campo>
        <Erro msg={erro} />{msg && <p className="sucesso">{msg}</p>}
        <button>Salvar</button>
      </form>
      <h2>Minhas candidaturas</h2>
      {apps.length === 0 ? <p className="quieto">Você ainda não se candidatou.</p> : (
        <ul className="lista">{apps.map((a) => <li key={a.id}><b>{a.vaga}</b> · {a.empresa}<br /><span className="quieto">{STATUS[a.status] || a.status}</span></li>)}</ul>
      )}
    </div>
  )
}
