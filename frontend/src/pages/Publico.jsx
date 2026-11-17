import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { homeDe, useAuth } from '../auth'
import { Campo, Erro, SelectLocal } from '../components'

export function Home() {
  return (
    <div className="home">
      <section className="hero">
        <h1>Seu currículo pronto <span>só falando</span>.</h1>
        <p>Conte o que você já fez. A gente transforma em currículo, mostra cursos baratos e vagas perto da sua casa.</p>
        <Link to="/cadastro?tipo=candidato" className="botao grande">🎤 Quero trabalhar</Link>
        <Link to="/cadastro?tipo=empresa" className="botao grande secundario">🏢 Sou empresa e quero contratar</Link>
        <p className="quieto">Já tem conta? <Link to="/entrar">Entrar</Link></p>
      </section>
      <section className="passos">
        <div><b>1. Fale</b><p>Responda perguntas simples com sua voz. Bico e trabalho sem carteira também contam.</p></div>
        <div><b>2. Aprenda</b><p>Cursos grátis ou baratos, presenciais ou online, perto de você.</p></div>
        <div><b>3. Trabalhe</b><p>Vagas perto de casa, inclusive em empresas que treinam você.</p></div>
      </section>
      <p className="centro"><Link to="/vagas">Ver vagas</Link> · <Link to="/cursos">Ver cursos</Link> · <Link to="/cadastro?tipo=parceiro">Sou associação / ONG</Link></p>
    </div>
  )
}

export function Entrar() {
  const { entrar } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ login: '', senha: '' })
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(false)

  async function enviar(e) {
    e.preventDefault(); setErro(''); setCarregando(true)
    try {
      const data = await api('/api/auth/login', { method: 'POST', body: f })
      entrar(data); nav(homeDe(data.user.role))
    } catch (e2) { setErro(e2.message) } finally { setCarregando(false) }
  }

  return (
    <form className="form estreito" onSubmit={enviar}>
      <h1>Entrar</h1>
      <Campo label="Telefone ou e-mail"><input value={f.login} onChange={(e) => setF({ ...f, login: e.target.value })} inputMode="email" autoComplete="username" required /></Campo>
      <Campo label="Senha"><input type="password" value={f.senha} onChange={(e) => setF({ ...f, senha: e.target.value })} autoComplete="current-password" required /></Campo>
      <Erro msg={erro} />
      <button className="grande" disabled={carregando}>{carregando ? 'Entrando…' : 'Entrar'}</button>
      <p className="quieto">Não tem conta? <Link to="/cadastro">Criar conta grátis</Link></p>
    </form>
  )
}

export function Cadastro() {
  const [params] = useSearchParams()
  const { entrar } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ role: params.get('tipo') || 'candidato', nome: '', login: '', senha: '', bairro: '', razao_social: '', cnpj: '', consentimento_lgpd: false })
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function enviar(e) {
    e.preventDefault(); setErro(''); setCarregando(true)
    try {
      const data = await api('/api/auth/register', { method: 'POST', body: f })
      entrar(data); nav(f.role === 'candidato' ? '/entrevista' : homeDe(f.role))
    } catch (e2) { setErro(e2.message) } finally { setCarregando(false) }
  }

  const cand = f.role === 'candidato'
  return (
    <form className="form estreito" onSubmit={enviar}>
      <h1>Criar conta grátis</h1>
      <div className="abas">
        {[['candidato', 'Quero trabalhar'], ['empresa', 'Empresa'], ['parceiro', 'Associação / ONG']].map(([v, l]) => (
          <button type="button" key={v} className={f.role === v ? 'ativa' : ''} onClick={() => setF({ ...f, role: v })}>{l}</button>
        ))}
      </div>
      <Campo label={cand ? 'Seu nome' : 'Seu nome (responsável)'}><input value={f.nome} onChange={set('nome')} required autoComplete="name" /></Campo>
      {f.role === 'empresa' && <>
        <Campo label="Nome da empresa"><input value={f.razao_social} onChange={set('razao_social')} required /></Campo>
        <Campo label="CNPJ (opcional)"><input value={f.cnpj} onChange={set('cnpj')} inputMode="numeric" /></Campo>
      </>}
      <Campo label={cand ? 'Seu celular (WhatsApp)' : 'E-mail ou telefone'} dica={cand ? 'Vai ser seu login. Só números, com DDD.' : undefined}>
        <input value={f.login} onChange={set('login')} required inputMode={cand ? 'tel' : 'email'} />
      </Campo>
      <Campo label="Crie uma senha" dica="Pelo menos 4 números ou letras."><input type="password" value={f.senha} onChange={set('senha')} minLength={4} required autoComplete="new-password" /></Campo>
      {f.role !== 'parceiro' && (
        <Campo label={cand ? 'Onde você mora?' : 'Onde fica a empresa?'}>
          <SelectLocal value={f.bairro} onChange={(v) => setF({ ...f, bairro: v })} />
        </Campo>
      )}
      {cand && (
        <label className="check">
          <input type="checkbox" checked={f.consentimento_lgpd} onChange={set('consentimento_lgpd')} />
          <span>Autorizo o empregoFacil a guardar o que eu falar para montar meu currículo e mostrar para empresas quando eu me candidatar. Meu endereço exato nunca é mostrado.</span>
        </label>
      )}
      <Erro msg={erro} />
      <button className="grande" disabled={carregando}>{carregando ? 'Criando…' : 'Criar conta'}</button>
      <p className="quieto">Já tem conta? <Link to="/entrar">Entrar</Link></p>
    </form>
  )
}
