import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check, FileText, FileUp, Mic, Pencil, Printer, RefreshCw, Sparkles, Square, Trash2, Volume2 } from 'lucide-react'
import { abrirArquivo, api, enviarArquivo } from '../api'
import { useAuth } from '../auth'
import { Carregando, Erro } from '../components'
import { falar, pararFala } from '../voz'

function textoParaOuvir(c) {
  const partes = [`Currículo de ${c.nome}.`, c.objetivo, c.resumo]
  ;(c.experiencias || []).forEach((e) => partes.push(`${e.cargo}. ${e.periodo || ''}. ${e.descricao || ''}`))
  if (c.habilidades?.length) partes.push('Habilidades: ' + c.habilidades.join(', ') + '.')
  if (c.formacao) partes.push('Estudos: ' + c.formacao)
  if (c.disponibilidade) partes.push('Disponibilidade: ' + c.disponibilidade)
  return partes.filter(Boolean).join(' ')
}

// Escolha inicial: fazer agora é SEMPRE a primeira opção (ninguém pode desistir por não ter currículo).
function SemCurriculo() {
  return (
    <div>
      <h1>Meu currículo</h1>
      <p>Não tem currículo? <b>Sem problema.</b> A gente monta com você agora.</p>
      <Link to="/entrevista" className="opcao-principal">
        <span className="opcao-icone"><Mic size={34} strokeWidth={2} /></span>
        <span>
          <b>Fazer meu currículo agora</b>
          <small>Falando ou escrevendo. Leva uns 5 minutos.</small>
        </span>
      </Link>
      <div className="ou"><span>ou</span></div>
      <Link to="/curriculo/enviar" className="botao secundario largo"><FileUp size={20} />Já tenho um currículo pronto</Link>
      <p className="quieto centro" style={{ fontSize: '.92rem' }}>PDF, Word ou foto do currículo em papel.</p>
    </div>
  )
}

export function EnviarCurriculo() {
  const { meta } = useAuth()
  const nav = useNavigate()
  const entrada = useRef(null)
  const [arquivo, setArquivo] = useState(null)
  const [modo, setModo] = useState('atualizar')
  const [areas, setAreas] = useState([])
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  function escolher(e) {
    const f = e.target.files?.[0]
    setErro('')
    if (!f) return
    if (f.size > 5 * 1024 * 1024) { setErro('O arquivo passa de 5 MB. Tente uma foto com menos qualidade ou um PDF.'); return }
    setArquivo(f)
  }

  async function enviar() {
    setErro('')
    if (modo === 'usar' && areas.length === 0) { setErro('Escolha pelo menos uma área em que você quer trabalhar.'); return }
    setEnviando(true)
    try {
      await enviarArquivo('/api/candidato/curriculo/arquivo', { arquivo, modo, categorias: areas.join(',') })
      nav('/curriculo')
    } catch (e) { setErro(e.message) } finally { setEnviando(false) }
  }

  const alternar = (id) => setAreas(areas.includes(id) ? areas.filter((a) => a !== id) : [...areas, id])

  return (
    <div className="form">
      <h1 style={{ marginBottom: 0 }}>Enviar meu currículo</h1>
      <input ref={entrada} type="file" accept=".pdf,.docx,image/jpeg,image/png" onChange={escolher} hidden />
      <button type="button" className="area-arquivo" onClick={() => entrada.current?.click()}>
        {arquivo ? <><FileText size={34} /><b>{arquivo.name}</b><small>Toque para trocar</small></>
          : <><FileUp size={34} /><b>Escolher arquivo ou tirar foto</b><small>PDF, Word (.docx) ou foto, até 5 MB</small></>}
      </button>

      {arquivo && <>
        <h2 style={{ margin: '.6rem 0 0' }}>O que você quer fazer?</h2>
        <label className={`opcao ${modo === 'atualizar' ? 'ativa' : ''}`}>
          <input type="radio" name="modo" checked={modo === 'atualizar'} onChange={() => setModo('atualizar')} />
          <span><b><Sparkles size={18} /> Melhorar e atualizar</b>
            <small>A gente lê seu currículo e organiza no modelo do Emprego Fácil. Você confere, corrige e pode acrescentar coisas novas.</small></span>
        </label>
        <label className={`opcao ${modo === 'usar' ? 'ativa' : ''}`}>
          <input type="radio" name="modo" checked={modo === 'usar'} onChange={() => setModo('usar')} />
          <span><b><FileText size={18} /> Usar do jeito que está</b>
            <small>As empresas recebem o seu arquivo, sem mudança nenhuma.</small></span>
        </label>
        {modo === 'usar' && (
          <div className="campo">
            <span>Em quais áreas você quer trabalhar?</span>
            <div className="chips">{meta.categorias.filter((c) => c.id !== 'outros').map((c) => (
              <button type="button" key={c.id} className={`chip ${areas.includes(c.id) ? 'ativa' : ''}`} aria-pressed={areas.includes(c.id)} onClick={() => alternar(c.id)}>{c.nome}</button>
            ))}</div>
            <small className="quieto">Assim a gente mostra as vagas certas para você.</small>
          </div>
        )}
        <Erro msg={erro} />
        <button className="grande" onClick={enviar} disabled={enviando}>
          {enviando ? (modo === 'atualizar' ? 'Lendo seu currículo…' : 'Enviando…') : modo === 'atualizar' ? 'Enviar e melhorar' : 'Enviar e usar'}
        </button>
      </>}
      {!arquivo && <Erro msg={erro} />}
      <p className="quieto centro">Não tem o arquivo aí? <Link to="/entrevista">Faça agora falando ou escrevendo</Link></p>
    </div>
  )
}

function CartaoArquivo({ cv, onMudou, setErro }) {
  const [ocupado, setOcupado] = useState('')
  const usando = cv.usar_arquivo

  async function acao(nome, fn) {
    setErro(''); setOcupado(nome)
    try { const r = await fn(); onMudou(r) } catch (e) { setErro(e.message) } finally { setOcupado('') }
  }

  return (
    <div className={`card nao-imprimir ${usando ? 'arquivo-ativo' : ''}`}>
      <div className="vaga">
        <div className="icone-area"><FileText size={28} /></div>
        <div className="vaga-corpo">
          <h3 style={{ wordBreak: 'break-word' }}>{cv.arquivo_nome}</h3>
          <p className="quieto" style={{ margin: '.2rem 0' }}>
            {usando ? 'As empresas recebem este arquivo.' : 'Arquivo guardado. As empresas recebem o currículo do Emprego Fácil abaixo.'}
          </p>
        </div>
      </div>
      <div className="acoes">
        <button className="secundario" onClick={() => abrirArquivo('/api/candidato/curriculo/arquivo', cv.arquivo_nome).catch((e) => setErro(e.message))}>Ver arquivo</button>
        {usando
          ? <button onClick={() => acao('melhorar', () => api('/api/candidato/curriculo/arquivo/atualizar', { method: 'POST' }))} disabled={!!ocupado}>
              <Sparkles size={18} />{ocupado === 'melhorar' ? 'Lendo…' : 'Melhorar com o Emprego Fácil'}</button>
          : <button className="secundario" onClick={() => acao('modo', () => api('/api/candidato/curriculo/modo?usar_arquivo=true', { method: 'PUT' }))} disabled={!!ocupado}>
              Mandar o arquivo original</button>}
        <Link className="botao secundario" to="/curriculo/enviar"><RefreshCw size={18} />Trocar</Link>
        <button className="link" onClick={() => acao('apagar', () => api('/api/candidato/curriculo/arquivo', { method: 'DELETE' }))} disabled={!!ocupado}>
          <Trash2 size={16} />Apagar arquivo</button>
      </div>
    </div>
  )
}

export default function Curriculo() {
  const { user, nomeCategoria } = useAuth()
  const [cv, setCv] = useState(undefined)
  const [perfil, setPerfil] = useState(null)
  const [editando, setEditando] = useState(false)
  const [c, setC] = useState(null)
  const [erro, setErro] = useState('')
  const [lendo, setLendo] = useState(false)

  useEffect(() => {
    api('/api/candidato/curriculo').then((r) => { setCv(r); setC(r?.conteudo) }).catch((e) => setErro(e.message))
    api('/api/candidato/perfil').then(setPerfil).catch(() => {})
    return pararFala
  }, [])

  const atualizar = (r) => { setCv(r); setC(r?.conteudo); setEditando(false) }

  async function salvar(confirmado) {
    setErro('')
    try { atualizar(await api('/api/candidato/curriculo', { method: 'PUT', body: { conteudo: c, confirmado } })) }
    catch (e) { setErro(e.message) }
  }

  function ouvirCv() {
    if (lendo) { pararFala(); setLendo(false); return }
    setLendo(true); falar(textoParaOuvir(c), { onFim: () => setLendo(false) })
  }

  if (cv === undefined) return erro ? <Erro msg={erro} /> : <Carregando />
  if (!cv) return <SemCurriculo />

  // Só o arquivo, do jeito que está
  if (cv.usar_arquivo && cv.origem === 'arquivo') return (
    <div>
      <h1>Meu currículo</h1>
      <Erro msg={erro} />
      <CartaoArquivo cv={cv} onMudou={atualizar} setErro={setErro} />
      <p><b>Áreas:</b> {(cv.categorias || []).map(nomeCategoria).join(', ')}</p>
      <div className="caixa-destaque">
        <p style={{ marginTop: 0 }}>Quer um currículo mais completo? Você pode <b>melhorar este arquivo</b> ou fazer um novo, falando ou escrevendo.</p>
        <Link className="botao secundario" to="/entrevista"><Mic size={18} />Fazer por voz</Link>
      </div>
      <p className="quieto"><Link to="/vagas">Ver vagas para mim →</Link></p>
    </div>
  )

  const setExp = (idx, k, v) => setC({ ...c, experiencias: c.experiencias.map((e, j) => (j === idx ? { ...e, [k]: v } : e)) })
  const veioDoArquivo = cv.origem === 'arquivo_atualizado'

  return (
    <div>
      <h1 className="nao-imprimir">Meu currículo</h1>
      <div className="acoes nao-imprimir">
        <button onClick={ouvirCv}>{lendo ? <><Square size={18} fill="currentColor" />Parar</> : <><Volume2 size={20} />Ouvir</>}</button>
        <button className="secundario" onClick={() => setEditando(!editando)}><Pencil size={18} />{editando ? 'Cancelar' : 'Corrigir'}</button>
        <button className="secundario" onClick={() => window.print()}><Printer size={18} />Salvar PDF</button>
        <Link className="botao secundario" to="/entrevista"><Mic size={18} />Refazer</Link>
        {!cv.arquivo_nome && <Link className="botao secundario" to="/curriculo/enviar"><FileUp size={18} />Enviar arquivo</Link>}
      </div>
      {!cv.confirmado && !editando && (
        <div className="banner nao-imprimir" style={{ display: 'block' }}>
          <p style={{ margin: '0 0 .8rem' }}>
            {veioDoArquivo
              ? <>Lemos o seu currículo e organizamos aqui. <b>Confira com calma</b>: corrija o que estiver errado e acrescente o que mudou.</>
              : 'Ouça ou leia com calma. Está tudo certo? Só o que você falou entra no currículo.'}
          </p>
          <div className="acoes" style={{ margin: 0 }}>
            <button onClick={() => salvar(true)}><Check size={20} />Está certo</button>
            {veioDoArquivo && <button className="secundario" onClick={() => setEditando(true)}><Pencil size={18} />Corrigir</button>}
          </div>
        </div>
      )}
      <Erro msg={erro} />

      <article className="curriculo">
        <h1>{c.nome || user?.nome}</h1>
        <p className="quieto">{[perfil?.telefone, perfil?.bairro, perfil?.cidade].filter(Boolean).join(' · ')}</p>

        {(c.objetivo || editando) && <h2>Objetivo</h2>}
        {editando ? <textarea value={c.objetivo || ''} onChange={(e) => setC({ ...c, objetivo: e.target.value })} /> : c.objetivo && <p>{c.objetivo}</p>}

        {(c.resumo || editando) && <h2>Resumo</h2>}
        {editando ? <textarea value={c.resumo || ''} onChange={(e) => setC({ ...c, resumo: e.target.value })} /> : c.resumo && <p>{c.resumo}</p>}

        {(c.experiencias?.length > 0 || editando) && <h2>Experiência</h2>}
        {(c.experiencias || []).map((e, idx) => (
          <div key={idx} className="exp">
            {editando ? (
              <>
                <input value={e.cargo} onChange={(ev) => setExp(idx, 'cargo', ev.target.value)} placeholder="Função" />
                <input value={e.periodo || ''} onChange={(ev) => setExp(idx, 'periodo', ev.target.value)} placeholder="Quanto tempo" />
                <input value={e.local || ''} onChange={(ev) => setExp(idx, 'local', ev.target.value)} placeholder="Onde (empresa, casa de família, por conta…)" />
                <textarea value={e.descricao || ''} onChange={(ev) => setExp(idx, 'descricao', ev.target.value)} placeholder="O que você fazia" />
                <button className="link" onClick={() => setC({ ...c, experiencias: c.experiencias.filter((_, j) => j !== idx) })}>Remover</button>
              </>
            ) : (
              <>
                <h3>{e.cargo}{e.periodo ? <span className="quieto"> · {e.periodo}</span> : null}</h3>
                {e.local && <p className="quieto">{e.local}</p>}
                {e.descricao && <p>{e.descricao}</p>}
              </>
            )}
          </div>
        ))}
        {editando && <button className="link" onClick={() => setC({ ...c, experiencias: [{ cargo: '', periodo: '', local: '', descricao: '' }, ...(c.experiencias || [])] })}>+ Acrescentar experiência</button>}

        {(c.habilidades?.length > 0 || editando) && <h2>Habilidades</h2>}
        {editando
          ? <textarea value={(c.habilidades || []).join(', ')} onChange={(e) => setC({ ...c, habilidades: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} placeholder="Separe por vírgula" />
          : <ul>{(c.habilidades || []).map((h) => <li key={h}>{h}</li>)}</ul>}

        {(c.formacao || editando) && <h2>Estudos</h2>}
        {editando ? <textarea value={c.formacao || ''} onChange={(e) => setC({ ...c, formacao: e.target.value })} /> : c.formacao && <p>{c.formacao}</p>}

        {(c.disponibilidade || editando) && <h2>Disponibilidade</h2>}
        {editando ? <textarea value={c.disponibilidade || ''} onChange={(e) => setC({ ...c, disponibilidade: e.target.value })} /> : c.disponibilidade && <p>{c.disponibilidade}</p>}
      </article>

      {editando && <div className="acoes"><button className="grande" onClick={() => salvar(true)}>Salvar</button></div>}
      {cv.arquivo_nome && <CartaoArquivo cv={cv} onMudou={atualizar} setErro={setErro} />}
      <p className="quieto nao-imprimir" style={{ marginTop: '1rem' }}>
        {cv.gerado_por === 'ia' ? 'Organizado com inteligência artificial.' : 'Organizado pelo assistente do Emprego Fácil.'} <Link to="/vagas">Ver vagas para mim →</Link>
      </p>
    </div>
  )
}
