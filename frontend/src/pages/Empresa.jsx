import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { abrirArquivo, api } from '../api'
import { useAuth } from '../auth'
import { Plus, Users } from 'lucide-react'
import { Campo, Carregando, Erro, SelectCategoria, SelectLocal, Selo } from '../components'

export function EmpresaVagas() {
  const [vagas, setVagas] = useState(null)
  const [erro, setErro] = useState('')
  useEffect(() => { api('/api/empresa/vagas').then(setVagas).catch((e) => setErro(e.message)) }, [])
  return (
    <div>
      <div className="card-topo"><h1>Minhas vagas</h1><Link to="/empresa/nova" className="botao"><Plus size={20} />Nova vaga</Link></div>
      <Erro msg={erro} />
      {vagas === null ? <Carregando /> : vagas.length === 0 ? (
        <div className="vazio"><p>Publique sua primeira vaga. Marque "treinamos você" para atrair quem ainda não tem experiência.</p></div>
      ) : vagas.map((v) => (
        <article className="card" key={v.id}>
          <div className="card-topo"><h3>{v.titulo}</h3><Selo tipo={v.status === 'aberta' ? 'bom' : ''}>{v.status}</Selo></div>
          <p className="quieto">{v.bairro || v.cidade}{v.com_treinamento ? ' · com treinamento' : ''}</p>
          <div className="acoes">
            <Link className="botao" to={`/empresa/vagas/${v.id}`}><Users size={18} />{v.total_candidatos} candidato(s)</Link>
            <Link className="botao secundario" to={`/empresa/vagas/${v.id}/editar`}>Editar</Link>
          </div>
        </article>
      ))}
    </div>
  )
}

const VAZIA = { titulo: '', categoria: '', descricao: '', salario: '', horario: '', bairro: '', vantagens: [], exige_experiencia: false,
  com_treinamento: false, tipo_treinamento: null, descricao_treinamento: '', curso_id: null, vagas: 1, status: 'aberta' }

export function VagaForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { meta } = useAuth()
  const [f, setF] = useState(VAZIA)
  const [cursos, setCursos] = useState([])
  const [erro, setErro] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  useEffect(() => {
    api('/api/cursos').then(setCursos).catch(() => {})
    if (id) api(`/api/vagas/${id}`).then((v) => setF({ ...VAZIA, ...v, curso_id: v.curso_id })).catch((e) => setErro(e.message))
  }, [id])

  async function salvar(e) {
    e.preventDefault(); setErro('')
    const body = { ...f, vagas: Number(f.vagas) || 1, curso_id: f.curso_id ? Number(f.curso_id) : null,
      tipo_treinamento: f.com_treinamento ? (f.tipo_treinamento || 'junto') : null }
    try {
      await api(id ? `/api/empresa/vagas/${id}` : '/api/empresa/vagas', { method: id ? 'PUT' : 'POST', body })
      nav('/empresa')
    } catch (e2) { setErro(e2.message) }
  }

  const toggleVantagem = (v) => setF({ ...f, vantagens: f.vantagens.includes(v) ? f.vantagens.filter((x) => x !== v) : [...f.vantagens, v] })

  return (
    <form className="form" onSubmit={salvar}>
      <h1>{id ? 'Editar vaga' : 'Nova vaga'}</h1>
      <Campo label="Função"><input value={f.titulo} onChange={set('titulo')} placeholder="Ex.: Auxiliar de cozinha" required /></Campo>
      <Campo label="Área"><SelectCategoria value={f.categoria} onChange={(v) => setF({ ...f, categoria: v })} vazio="Escolha a área" /></Campo>
      <Campo label="O que a pessoa vai fazer"><textarea value={f.descricao} onChange={set('descricao')} required placeholder="Use palavras simples." /></Campo>
      <Campo label="Salário"><input value={f.salario || ''} onChange={set('salario')} placeholder="Ex.: R$ 1.700 + benefícios" /></Campo>
      <Campo label="Horário"><input value={f.horario || ''} onChange={set('horario')} placeholder="Ex.: Seg a sex, 8h às 17h" /></Campo>
      <Campo label="Onde é o trabalho"><SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} vazio="Bairro ou cidade" /></Campo>
      <Campo label="Vantagens">
        <div className="chips">{meta.vantagens.map((v) => (
          <button type="button" key={v} className={`chip ${f.vantagens.includes(v) ? 'ativa' : ''}`} onClick={() => toggleVantagem(v)}>{v}</button>
        ))}</div>
      </Campo>
      <label className="check"><input type="checkbox" checked={f.exige_experiencia} onChange={set('exige_experiencia')} /> Exige experiência</label>

      <div className="caixa-destaque">
        <label className="check"><input type="checkbox" checked={f.com_treinamento} onChange={set('com_treinamento')} /> <b>Treinamos a pessoa</b></label>
        {f.com_treinamento && <>
          <Campo label="Quando é o treinamento">
            <select value={f.tipo_treinamento || 'junto'} onChange={set('tipo_treinamento')}>
              <option value="junto">Junto com o trabalho</option><option value="antes">Antes de começar</option>
            </select>
          </Campo>
          <Campo label="Como é o treinamento"><textarea value={f.descricao_treinamento || ''} onChange={set('descricao_treinamento')} /></Campo>
          <Campo label="Ligar a um curso (opcional)" dica="Quem fizer o curso vê sua vaga em destaque.">
            <select value={f.curso_id || ''} onChange={set('curso_id')}>
              <option value="">Nenhum</option>
              {cursos.map((c) => <option key={c.id} value={c.id}>{c.titulo} — {c.ofertante}</option>)}
            </select>
          </Campo>
        </>}
      </div>

      <Campo label="Quantas vagas"><input type="number" min="1" value={f.vagas} onChange={set('vagas')} /></Campo>
      {id && <Campo label="Situação">
        <select value={f.status} onChange={set('status')}><option value="aberta">Aberta</option><option value="pausada">Pausada</option><option value="encerrada">Encerrada</option></select>
      </Campo>}
      <Erro msg={erro} />
      <button className="grande">{id ? 'Salvar' : 'Publicar vaga'}</button>
    </form>
  )
}

const STATUS = [['vista', 'Vista'], ['entrevista', 'Chamar p/ entrevista'], ['contratado', 'Contratado'], ['recusada', 'Não seguiu']]

export function Candidatos() {
  const { id } = useParams()
  const [lista, setLista] = useState(null)
  const [vaga, setVaga] = useState(null)
  const [aberto, setAberto] = useState(null)
  const [erro, setErro] = useState('')

  const carregar = () => api(`/api/empresa/vagas/${id}/candidatos`).then(setLista).catch((e) => setErro(e.message))
  useEffect(() => { carregar(); api(`/api/vagas/${id}`).then(setVaga).catch(() => {}) }, [id])

  async function mudar(appId, status) {
    try { await api(`/api/empresa/candidaturas/${appId}`, { method: 'PUT', body: { status } }); carregar() } catch (e) { setErro(e.message) }
  }

  return (
    <div>
      <Link to="/empresa">← Minhas vagas</Link>
      <h1>{vaga?.titulo || 'Candidatos'}</h1>
      <Erro msg={erro} />
      {lista === null ? <Carregando /> : lista.length === 0 ? <p className="quieto">Ninguém se candidatou ainda.</p> : lista.map((c) => (
        <article className="card" key={c.application_id}>
          <div className="card-topo"><h3>{c.nome}</h3>{c.distancia_km != null && <span className="distancia">{c.distancia_km < 1 ? "Mesmo bairro" : `${c.distancia_km} km`}</span>}</div>
          <p className="quieto">{c.bairro} · {c.telefone && <a href={`https://wa.me/55${c.telefone}`} target="_blank" rel="noreferrer">WhatsApp {c.telefone}</a>}</p>
          {c.curriculo?.objetivo && <p>{c.curriculo.objetivo}</p>}
          {c.mensagem && <p>“{c.mensagem}”</p>}
          {aberto === c.application_id && c.curriculo && (
            <div className="detalhe">
              <p>{c.curriculo.resumo}</p>
              {(c.curriculo.experiencias || []).map((e, i) => <p key={i}><b>{e.cargo}</b>{e.periodo ? ` · ${e.periodo}` : ''}<br />{e.descricao}</p>)}
              {c.curriculo.habilidades?.length > 0 && <p>Habilidades: {c.curriculo.habilidades.join(', ')}</p>}
              {c.curriculo.formacao && <p>Estudos: {c.curriculo.formacao}</p>}
              {c.curriculo.disponibilidade && <p>Disponibilidade: {c.curriculo.disponibilidade}</p>}
            </div>
          )}
          <div className="acoes">
            {c.usar_arquivo
              ? <button onClick={() => abrirArquivo(`/api/empresa/candidaturas/${c.application_id}/arquivo`, c.arquivo_nome).catch((e) => setErro(e.message))}>{/\.docx$/i.test(c.arquivo_nome || '') ? 'Baixar currículo' : 'Abrir currículo'}</button>
              : <button className="secundario" onClick={() => setAberto(aberto === c.application_id ? null : c.application_id)}>{aberto === c.application_id ? 'Fechar' : 'Ver currículo'}</button>}
            {!c.usar_arquivo && c.arquivo_nome && <button className="link" onClick={() => abrirArquivo(`/api/empresa/candidaturas/${c.application_id}/arquivo`, c.arquivo_nome).catch((e) => setErro(e.message))}>Arquivo original</button>}
            <select value={c.status} onChange={(e) => mudar(c.application_id, e.target.value)}>
              {c.status === 'enviada' && <option value="enviada">Nova</option>}
              {STATUS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
        </article>
      ))}
    </div>
  )
}
