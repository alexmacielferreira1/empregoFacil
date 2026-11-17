import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

  return (
    <div className="entrevista">
      <p className="quieto">Pergunta {i + 1} de {perguntas.length}</p>
      <div className="barra"><div style={{ width: `${((i + 1) / perguntas.length) * 100}%` }} /></div>
      <h2 className="pergunta">{atual.texto}</h2>
      <button className="link" onClick={() => falar(atual.texto)}>🔊 Ouvir a pergunta de novo</button>

      <div className="microfone">
        {temReconhecimento ? (
          <button className={`mic ${gravando ? 'gravando' : ''}`} onClick={gravando ? parar : comecar} aria-label={gravando ? 'Parar de gravar' : 'Falar resposta'}>
            {gravando ? '■' : '🎤'}
          </button>
        ) : (
          <p className="aviso">Seu navegador não reconhece voz aqui. Toque na caixa abaixo e use o 🎤 do teclado do celular.</p>
        )}
        <p className="quieto">{gravando ? 'Estou ouvindo… toque para parar.' : 'Toque no microfone e fale à vontade.'}</p>
      </div>

      <textarea
        rows={5}
        value={(respostas[atual.id] || '') + (parcial ? ' ' + parcial : '')}
        onChange={(e) => setRespostas({ ...respostas, [atual.id]: e.target.value })}
        placeholder="Sua resposta aparece aqui. Você pode corrigir digitando."
      />
      <Erro msg={erro} />

      <div className="acoes">
        <button className="secundario" onClick={() => ir(-1)} disabled={i === 0}>Voltar</button>
        {!ultima && <button onClick={() => ir(1)}>{(respostas[atual.id] || '').trim() ? 'Próxima' : 'Pular'}</button>}
        {ultima && <button onClick={gerar} disabled={gerando || respondidas === 0}>{gerando ? 'Montando seu currículo…' : '✨ Montar meu currículo'}</button>}
      </div>
      {!ultima && respondidas >= 2 && (
        <button className="link" onClick={gerar} disabled={gerando}>Já respondi o suficiente, montar agora</button>
      )}
    </div>
  )
}
