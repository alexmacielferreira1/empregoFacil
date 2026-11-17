// Voz no navegador: reconhecimento (fala -> texto) e síntese (texto -> fala).
// Funciona no Chrome do Android e no Chrome/Edge do computador. Onde não houver,
// a pessoa digita (ou usa o microfone do teclado do celular).

const SR = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null

export const temReconhecimento = !!SR
export const temSintese = typeof window !== 'undefined' && 'speechSynthesis' in window

export function falar(texto, { onFim } = {}) {
  if (!temSintese || !texto) { onFim?.(); return }
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(texto)
  u.lang = 'pt-BR'
  u.rate = 0.95
  const voz = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith('pt'))
  if (voz) u.voice = voz
  u.onend = () => onFim?.()
  u.onerror = () => onFim?.()
  window.speechSynthesis.speak(u)
}

export function pararFala() {
  if (temSintese) window.speechSynthesis.cancel()
}

// Retorna um controlador { parar() }. onTexto recebe (textoFinalAcumulado, textoParcial).
export function ouvir({ onTexto, onFim, onErro }) {
  if (!SR) { onErro?.('Seu navegador não reconhece voz. Use o microfone do teclado ou digite.'); return null }
  const rec = new SR()
  rec.lang = 'pt-BR'
  rec.continuous = true
  rec.interimResults = true
  let final = ''
  let parado = false
  rec.onresult = (e) => {
    let parcial = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript
      if (e.results[i].isFinal) final += (final ? ' ' : '') + t.trim()
      else parcial += t
    }
    onTexto?.(final, parcial)
  }
  rec.onerror = (e) => {
    if (e.error === 'not-allowed') onErro?.('Permita o uso do microfone para falar.')
    else if (e.error !== 'no-speech' && e.error !== 'aborted') onErro?.('Não consegui ouvir. Tente de novo.')
  }
  rec.onend = () => {
    // o Chrome encerra sozinho após silêncio; reinicia até a pessoa tocar em "Parar"
    if (!parado) { try { rec.start() } catch { onFim?.(final) } } else onFim?.(final)
  }
  rec.start()
  return { parar() { parado = true; rec.stop() } }
}
