const BASE = import.meta.env.VITE_API_URL || ''

export function getToken() {
  try { return localStorage.getItem('ef_token') } catch { return null }
}

export function setSession(token, user) {
  try {
    if (token) {
      localStorage.setItem('ef_token', token)
      localStorage.setItem('ef_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('ef_token')
      localStorage.removeItem('ef_user')
    }
  } catch { /* navegador sem storage */ }
}

export function getStoredUser() {
  try { return JSON.parse(localStorage.getItem('ef_user') || 'null') } catch { return null }
}

export async function api(path, { method = 'GET', body, params } = {}) {
  let url = BASE + path
  if (params) {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '' && v !== false) q.set(k, v) })
    const s = q.toString()
    if (s) url += '?' + s
  }
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401) { setSession(null) }
    let msg = 'Algo deu errado. Tente de novo.'
    if (data?.detail) msg = Array.isArray(data.detail) ? 'Confira os campos preenchidos.' : data.detail
    throw new Error(msg)
  }
  return data
}

export const brl = (v) => (v === 0 ? 'Grátis' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }))

// Envio de arquivo (multipart). Não define Content-Type: o navegador coloca o boundary.
export async function enviarArquivo(path, campos) {
  const fd = new FormData()
  Object.entries(campos).forEach(([k, v]) => fd.append(k, v))
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(BASE + path, { method: 'POST', headers, body: fd })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(data?.detail && !Array.isArray(data.detail) ? data.detail : 'Não foi possível enviar o arquivo.')
  return data
}

// Abre um arquivo protegido (precisa do token): PDF e foto numa aba nova; Word é baixado.
export async function abrirArquivo(path, nome = '') {
  const baixar = /\.docx$/i.test(nome)
  const aba = baixar ? null : window.open('', '_blank') // abre já no clique, senão o navegador bloqueia
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(BASE + path, { headers })
  if (!res.ok) { aba?.close(); throw new Error('Não foi possível abrir o arquivo.') }
  const url = URL.createObjectURL(await res.blob())
  if (baixar || !aba) {
    const a = document.createElement('a')
    a.href = url; a.download = nome || 'curriculo'; document.body.appendChild(a); a.click(); a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } else aba.location.href = url
}
