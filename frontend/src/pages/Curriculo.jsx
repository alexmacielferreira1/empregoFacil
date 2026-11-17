import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
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

export default function Curriculo() {
  const { user } = useAuth()
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

  async function salvar(confirmado) {
    setErro('')
    try {
      const r = await api('/api/candidato/curriculo', { method: 'PUT', body: { conteudo: c, confirmado } })
      setCv(r); setC(r.conteudo); setEditando(false)
    } catch (e) { setErro(e.message) }
  }

  function ouvirCv() {
    if (lendo) { pararFala(); setLendo(false); return }
    setLendo(true); falar(textoParaOuvir(c), { onFim: () => setLendo(false) })
  }

  if (cv === undefined) return erro ? <Erro msg={erro} /> : <Carregando />
  if (!cv) return (
    <div className="vazio">
      <h2>Você ainda não tem currículo</h2>
      <p>Leva uns 5 minutos. É só responder falando.</p>
      <Link className="botao grande" to="/entrevista">🎤 Começar</Link>
    </div>
  )

  const setExp = (idx, k, v) => setC({ ...c, experiencias: c.experiencias.map((e, j) => (j === idx ? { ...e, [k]: v } : e)) })

  return (
    <div>
      <div className="acoes nao-imprimir">
        <button onClick={ouvirCv}>{lendo ? '■ Parar' : '🔊 Ouvir meu currículo'}</button>
        <button className="secundario" onClick={() => setEditando(!editando)}>{editando ? 'Cancelar' : '✏️ Corrigir'}</button>
        <button className="secundario" onClick={() => window.print()}>🖨️ Salvar PDF</button>
      </div>
      {!cv.confirmado && !editando && (
        <div className="aviso nao-imprimir">
          <p>Ouça ou leia com calma. Está tudo certo? Só o que você falou entra no currículo.</p>
          <div className="acoes">
            <button onClick={() => salvar(true)}>✔ Está certo</button>
            <Link to="/entrevista" className="botao secundario">Responder de novo</Link>
          </div>
        </div>
      )}
      <Erro msg={erro} />

      <article className="curriculo">
        <h1>{c.nome || user?.nome}</h1>
        <p className="quieto">{[perfil?.telefone, perfil?.bairro, perfil?.cidade].filter(Boolean).join(' · ')}</p>

        <h2>Objetivo</h2>
        {editando ? <textarea value={c.objetivo || ''} onChange={(e) => setC({ ...c, objetivo: e.target.value })} /> : <p>{c.objetivo}</p>}

        <h2>Resumo</h2>
        {editando ? <textarea value={c.resumo || ''} onChange={(e) => setC({ ...c, resumo: e.target.value })} /> : <p>{c.resumo}</p>}

        {(c.experiencias?.length > 0 || editando) && <h2>Experiência</h2>}
        {(c.experiencias || []).map((e, idx) => (
          <div key={idx} className="exp">
            {editando ? (
              <>
                <input value={e.cargo} onChange={(ev) => setExp(idx, 'cargo', ev.target.value)} placeholder="Função" />
                <input value={e.periodo || ''} onChange={(ev) => setExp(idx, 'periodo', ev.target.value)} placeholder="Quanto tempo" />
                <textarea value={e.descricao || ''} onChange={(ev) => setExp(idx, 'descricao', ev.target.value)} />
                <button className="link" onClick={() => setC({ ...c, experiencias: c.experiencias.filter((_, j) => j !== idx) })}>Remover</button>
              </>
            ) : (
              <>
                <h3>{e.cargo}{e.periodo ? <span className="quieto"> · {e.periodo}</span> : null}</h3>
                {e.local && <p className="quieto">{e.local}</p>}
                <p>{e.descricao}</p>
              </>
            )}
          </div>
        ))}
        {editando && <button className="link" onClick={() => setC({ ...c, experiencias: [...(c.experiencias || []), { cargo: '', periodo: '', local: '', descricao: '' }] })}>+ Adicionar experiência</button>}

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
      <p className="quieto nao-imprimir">Feito com {cv.gerado_por === 'ia' ? 'inteligência artificial' : 'o assistente do empregoFacil'}. <Link to="/vagas">Ver vagas para mim →</Link></p>
    </div>
  )
}
