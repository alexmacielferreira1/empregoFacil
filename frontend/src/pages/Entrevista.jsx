import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Mic, Square, Volume2 } from 'lucide-react'
import { api } from '../api'
import { Carregando, Erro } from '../components'
import { falar, ouvir, pararFala, temReconhecimento } from '../voz'

export default function Entrevista() {
  const nav = useNavigate()
  const [perguntas, setPerguntas] = useState([])
  const [i, setI] = useState(0)
  const [respostas, setRespostas] = useState({})
  const [parcial, setParcial] = useState('')
  const [gravando, setGravando] = useState(false)
  const [erro, setErro] = useState('')
  const [gerando, setGerando] = useState(false)
  const rec = useRef(null)
  const base = useRef('')

  useEffect(() => {
    Promise.all([api('/api/candidato/entrevista/perguntas'), api('/api/candidato/curriculo')])
      .then(([p, cv]) => { setPerguntas(p); if (cv?.respostas) setRespostas(cv.respostas) })
      .catch((e) => setErro(e.message))
    return () => { rec.current?.parar(); pararFala() }
  }, [])

  const atual = perguntas[i]

  useEffect(() => { if (atual) falar(atual.texto) }, [atual?.id]) // lê a pergunta em voz alta

  function comecar() {
    setErro(''); pararFala()
    base.current = respostas[atual.id] ? respostas[atual.id] + ' ' : ''
    rec.current = ouvir({
      onTexto: (final, p) => { setRespostas((r) => ({ ...r, [atual.id]: (base.current + final).trim() })); setParcial(p) },
      onFim: () => { setGravando(false); setParcial('') },
      onErro: (m) => { setErro(m); setGravando(false) },
    })
    if (rec.current) setGravando(true)
  }

  function parar() { rec.current?.parar(); rec.current = null; setGravando(false); setParcial('') }
  function ir(delta) { parar(); setI((x) => Math.min(Math.max(x + delta, 0), perguntas.length - 1)) }

  async function gerar() {
    parar(); setErro(''); setGerando(true)
    try {
      await api('/api/candidato/curriculo/gerar', { method: 'POST', body: { respostas } })
      nav('/curriculo')
    } catch (e) { setErro(e.message) } finally { setGerando(false) }
  }

  if (!perguntas.length) return erro ? <Erro msg={erro} /> : <Carregando />
  const ultima = i === perguntas.length - 1
  const respondidas = perguntas.filter((p) => (respostas[p.id] || '').trim()).length
  const temResposta = (respostas[atual.id] || '').trim()

  return (
    <div className="entrevista">
      <h1>Currículo por voz</h1>
      <p style={{ margin: 0 }}>Pergunta {i + 1} de {perguntas.length}</p>
      <div className="barra" role="progressbar" aria-valuemin={1} aria-valuemax={perguntas.length} aria-valuenow={i + 1}>
        <div style={{ width: `${((i + 1) / perguntas.length) * 100}%` }} />
      </div>

      <h2 className="pergunta">{atual.titulo || atual.texto}</h2>
      {atual.detalhe && <p className="pergunta-detalhe">{atual.detalhe}</p>}
      <div className="centro"><button className="pilula" onClick={() => falar(atual.texto)}><Volume2 size={20} />Ouvir pergunta</button></div>

      <div className="painel-mic">
        {temReconhecimento ? (
          <>
            <button className={`mic ${gravando ? 'gravando' : ''}`} onClick={gravando ? parar : comecar} aria-label={gravando ? 'Parar de gravar' : 'Gravar resposta'}>
              {gravando ? <Square size={36} fill="currentColor" /> : <Mic size={46} strokeWidth={2} />}
            </button>
            <p className="rotulo">{gravando ? 'Ouvindo… toque para parar' : 'Gravar resposta'}</p>
          </>
        ) : (
          <p style={{ margin: 0 }}>Este navegador não reconhece voz. Toque na caixa abaixo e use o <b>microfone do teclado</b> do celular.</p>
        )}
      </div>

      <label className="campo">
        <span>Ou digite sua resposta</span>
        <textarea
          rows={4}
          value={(respostas[atual.id] || '') + (parcial ? ' ' + parcial : '')}
          onChange={(e) => setRespostas({ ...respostas, [atual.id]: e.target.value })}
          placeholder="Descreva aqui suas atividades…"
        />
      </label>
      <Erro msg={erro} />

      <div className="acoes" style={{ marginTop: '1rem', flexWrap: 'nowrap' }}>
        {i > 0 && <button className="secundario" onClick={() => ir(-1)} aria-label="Pergunta anterior"><ArrowLeft size={20} /></button>}
        {!ultima && <button className="grande" style={{ flex: 1 }} onClick={() => ir(1)}>{temResposta ? 'Próxima' : 'Pular'} <ArrowRight size={22} /></button>}
        {ultima && <button className="grande" style={{ flex: 1 }} onClick={gerar} disabled={gerando || respondidas === 0}>{gerando ? 'Montando seu currículo…' : 'Montar meu currículo'}</button>}
      </div>
      {!ultima && respondidas >= 2 && (
        <p className="centro"><button className="link" onClick={gerar} disabled={gerando}>Montar currículo agora</button></p>
      )}
    </div>
  )
}
