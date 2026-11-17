import { useEffect, useState } from 'react'
import { api, brl } from '../api'
import { Campo, Carregando, Erro, SelectCategoria, SelectLocal, Selo } from '../components'

export function Parceiro() {
  const [lista, setLista] = useState(null)
  const [f, setF] = useState({ nome: '', login: '', bairro: '', consentimento_lgpd: false })
  const [criado, setCriado] = useState(null)
  const [erro, setErro] = useState('')

  const carregar = () => api('/api/parceiro/candidatos').then(setLista).catch((e) => setErro(e.message))
  useEffect(() => { carregar() }, [])

  async function novaSenha(id) {
    setErro(''); setCriado(null)
    try { const r = await api(`/api/parceiro/candidatos/${id}/nova-senha`, { method: 'POST' }); setCriado({ ...r, nova: true }); window.scrollTo(0, 0) }
    catch (e) { setErro(e.message) }
  }

  async function enviar(e) {
    e.preventDefault(); setErro(''); setCriado(null)
    try {
      const r = await api('/api/parceiro/candidatos', { method: 'POST', body: f })
      setCriado(r); setF({ nome: '', login: '', bairro: '', consentimento_lgpd: false }); carregar()
    } catch (e2) { setErro(e2.message) }
  }

  return (
    <div>
      <h1>Cadastrar uma pessoa</h1>
      <p className="quieto">Para quem não consegue se cadastrar sozinho. Depois, entre com o telefone e a senha provisória dela para fazer a entrevista juntos.</p>
      <form className="form" onSubmit={enviar}>
        <Campo label="Nome da pessoa"><input value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} required /></Campo>
        <Campo label="Celular da pessoa"><input value={f.login} onChange={(e) => setF({ ...f, login: e.target.value })} inputMode="tel" required /></Campo>
        <Campo label="Onde mora"><SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} /></Campo>
        <label className="check"><input type="checkbox" checked={f.consentimento_lgpd} onChange={(e) => setF({ ...f, consentimento_lgpd: e.target.checked })} /> A pessoa autorizou este cadastro</label>
        <Erro msg={erro} />
        <button>Cadastrar</button>
      </form>
      {criado && (
        <div className="caixa-destaque ok">
          <p className="sucesso">{criado.nova ? `Senha nova de ${criado.nome}` : `${criado.nome} foi cadastrada.`}</p>
          <p>Login: <b>{criado.login}</b> · Senha provisória: <b>{criado.senha_provisoria}</b></p>
          <p className="quieto">Anote e entregue para a pessoa. Ela pode trocar depois.</p>
        </div>
      )}
      <h2>Pessoas que você cadastrou</h2>
      {lista === null ? <Carregando /> : lista.length === 0 ? <p className="quieto">Ninguém ainda.</p> : (
        <ul className="lista">{lista.map((p) => (
          <li key={p.id}>
            <b>{p.nome}</b> · {p.login} · {p.bairro || '—'} {p.tem_curriculo ? <Selo tipo="bom">Tem currículo</Selo> : <Selo>Sem currículo</Selo>}
            <br /><button className="link" onClick={() => novaSenha(p.id)}>Gerar senha nova</button>
          </li>
        ))}</ul>
      )}
    </div>
  )
}

export function Admin() {
  const [r, setR] = useState(null)
  const [users, setUsers] = useState([])
  const [avisos, setAvisos] = useState([])
  const [senha, setSenha] = useState(null)
  const [erro, setErro] = useState('')
  useEffect(() => {
    api('/api/admin/resumo').then(setR).catch((e) => setErro(e.message))
    api('/api/admin/usuarios').then(setUsers).catch(() => {})
    api('/api/admin/avisos').then(setAvisos).catch(() => {})
  }, [])
  async function novaSenha(id) {
    setErro('')
    try { setSenha(await api(`/api/admin/usuarios/${id}/nova-senha`, { method: 'POST' })); window.scrollTo(0, 0) } catch (e) { setErro(e.message) }
  }
  const ROT = { candidatos: 'Candidatos', curriculos: 'Currículos', empresas: 'Empresas', parceiros: 'Parceiros', vagas_abertas: 'Vagas abertas',
    vagas_com_treinamento: 'Vagas com treino', cursos: 'Cursos', candidaturas: 'Candidaturas', contratados: 'Contratados',
    avisos_whatsapp: 'Avisos WhatsApp', avisos_falharam: 'Avisos com falha' }
  return (
    <div>
      <h1>Painel</h1>
      <Erro msg={erro} />
      {senha && <div className="caixa-destaque ok"><p className="sucesso">Senha nova de {senha.nome}</p><p>Login: <b>{senha.login}</b> · Senha provisória: <b>{senha.senha_provisoria}</b></p></div>}
      {!r ? <Carregando /> : <div className="numeros">{Object.entries(ROT).map(([k, l]) => <div key={k}><b>{r[k]}</b><span>{l}</span></div>)}</div>}
      <h2>Últimos usuários</h2>
      <table className="tabela"><thead><tr><th>Nome</th><th>Login</th><th>Tipo</th><th></th></tr></thead>
        <tbody>{users.map((u) => <tr key={u.id}><td>{u.nome}</td><td>{u.login}</td><td>{u.role}</td>
          <td>{u.role !== 'admin' && <button className="link" onClick={() => novaSenha(u.id)}>Nova senha</button>}</td></tr>)}</tbody></table>
      <h2>Últimos avisos</h2>
      {avisos.length === 0 ? <p className="quieto">Nenhum aviso enviado ainda.</p> : (
        <table className="tabela"><thead><tr><th>Aviso</th><th>Para</th><th>Situação</th></tr></thead>
          <tbody>{avisos.map((a) => <tr key={a.id}><td>{a.resumo}<br /><span className="quieto">{a.tipo} · {new Date(a.created_at).toLocaleString('pt-BR')}</span></td>
            <td>{a.destino}</td><td>{a.status}{a.erro ? <><br /><span className="quieto">{a.erro}</span></> : null}</td></tr>)}</tbody></table>
      )}
    </div>
  )
}

const CURSO_VAZIO = { titulo: '', ofertante: '', categoria: '', descricao: '', modalidade: 'presencial', preco: 0, carga_horaria: '', certificado: true, bairro: '', horario: '', link: '', imagem_url: '', contato: '' }

export function AdminCursos() {
  const [lista, setLista] = useState(null)
  const [f, setF] = useState(CURSO_VAZIO)
  const [editId, setEditId] = useState(null)
  const [erro, setErro] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const carregar = () => api('/api/cursos').then(setLista).catch((e) => setErro(e.message))
  useEffect(() => { carregar() }, [])

  async function salvar(e) {
    e.preventDefault(); setErro('')
    const body = { ...f, preco: Number(f.preco) || 0, carga_horaria: f.carga_horaria ? Number(f.carga_horaria) : null, cidade: f.bairro ? 'Porto Alegre' : null }
    try {
      await api(editId ? `/api/cursos/${editId}` : '/api/cursos', { method: editId ? 'PUT' : 'POST', body })
      setF(CURSO_VAZIO); setEditId(null); carregar()
    } catch (e2) { setErro(e2.message) }
  }

  async function remover(id) {
    if (!window.confirm('Remover este curso?')) return
    try { await api(`/api/cursos/${id}`, { method: 'DELETE' }); carregar() } catch (e) { setErro(e.message) }
  }

  return (
    <div>
      <h1>Cursos</h1>
      <form className="form" onSubmit={salvar}>
        <h2>{editId ? 'Editar curso' : 'Novo curso'}</h2>
        <Campo label="Nome do curso"><input value={f.titulo} onChange={set('titulo')} required /></Campo>
        <Campo label="Quem oferece"><input value={f.ofertante} onChange={set('ofertante')} required placeholder="Senac, ONG, prefeitura…" /></Campo>
        <Campo label="Área"><SelectCategoria value={f.categoria} onChange={(v) => setF({ ...f, categoria: v })} vazio="Escolha a área" /></Campo>
        <Campo label="Modalidade"><select value={f.modalidade} onChange={set('modalidade')}><option value="presencial">Presencial</option><option value="online">Online</option></select></Campo>
        {f.modalidade === 'presencial' && <Campo label="Onde"><SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} /></Campo>}
        <Campo label="Preço (R$, 0 = grátis)"><input type="number" min="0" step="0.01" value={f.preco} onChange={set('preco')} /></Campo>
        <Campo label="Carga horária (h)"><input type="number" min="1" value={f.carga_horaria} onChange={set('carga_horaria')} /></Campo>
        <Campo label="Dias e horário"><input value={f.horario} onChange={set('horario')} /></Campo>
        <Campo label="Link de inscrição"><input value={f.link} onChange={set('link')} type="url" /></Campo>
        <Campo label="Contato"><input value={f.contato} onChange={set('contato')} /></Campo>
        <Campo label="Foto (link da imagem, opcional)" dica="Sem link, usa a foto da área em /img/cursos/<area>.jpg"><input value={f.imagem_url} onChange={set('imagem_url')} type="url" /></Campo>
        <Campo label="Descrição"><textarea value={f.descricao} onChange={set('descricao')} /></Campo>
        <label className="check"><input type="checkbox" checked={f.certificado} onChange={set('certificado')} /> Dá certificado</label>
        <Erro msg={erro} />
        <div className="acoes"><button>{editId ? 'Salvar' : 'Cadastrar curso'}</button>{editId && <button type="button" className="secundario" onClick={() => { setEditId(null); setF(CURSO_VAZIO) }}>Cancelar</button>}</div>
      </form>
      {lista === null ? <Carregando /> : (
        <table className="tabela"><thead><tr><th>Curso</th><th>Preço</th><th></th></tr></thead>
          <tbody>{lista.map((c) => (
            <tr key={c.id}><td>{c.titulo}<br /><span className="quieto">{c.ofertante}{c.exemplo ? ' · exemplo' : ''}</span></td><td>{brl(c.preco)}</td>
              <td><button className="link" onClick={() => { setEditId(c.id); setF({ ...CURSO_VAZIO, ...c, carga_horaria: c.carga_horaria || '', bairro: c.bairro || '', link: c.link || '', imagem_url: c.imagem_url || '', contato: c.contato || '', horario: c.horario || '', descricao: c.descricao || '' }); window.scrollTo(0, 0) }}>Editar</button>{' '}
                <button className="link" onClick={() => remover(c.id)}>Remover</button></td></tr>
          ))}</tbody></table>
      )}
    </div>
  )
}
