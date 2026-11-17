import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { homeDe, useAuth } from '../auth'
import { Building2, GraduationCap, Briefcase, Mic } from 'lucide-react'
import { Campo, Erro, SelectLocal } from '../components'

export function Home() {
  return (
    <div className="home">
      <section className="hero">
        <img className="hero-simbolo" src="/simbolo.svg" alt="" />
        <h1>Seu currículo pronto <span>só falando</span>.</h1>
        <p>Conte o que você já fez. A gente transforma em currículo, mostra cursos baratos e vagas perto da sua casa.</p>
        <Link to="/cadastro?tipo=candidato" className="botao grande"><Mic size={22} />Quero trabalhar</Link>
        <Link to="/cadastro?tipo=empresa" className="botao grande secundario"><Building2 size={22} />Sou empresa e quero contratar</Link>
        <p className="quieto">Já tem conta? <Link to="/entrar">Entrar</Link></p>
      </section>
      <section className="passos">
        <div className="passo"><div className="icone-area"><Mic size={28} /></div><div><b>1. Fale</b><p>Responda perguntas simples com sua voz. Bico e trabalho sem carteira também contam.</p></div></div>
        <div className="passo"><div className="icone-area"><GraduationCap size={28} /></div><div><b>2. Aprenda</b><p>Cursos grátis ou baratos, presenciais ou online, perto de você.</p></div></div>
        <div className="passo"><div className="icone-area"><Briefcase size={28} /></div><div><b>3. Trabalhe</b><p>Vagas perto de casa, inclusive em empresas que treinam você.</p></div></div>
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
      <p className="centro"><Link to="/recuperar">Esqueci minha senha</Link></p>
      <p className="quieto">Não tem conta? <Link to="/cadastro">Criar conta grátis</Link></p>
    </form>
  )
}

export function Cadastro() {
  const [params] = useSearchParams()
  const { entrar } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ role: params.get('tipo') || 'candidato', nome: '', login: '', senha: '', bairro: '', razao_social: '', cnpj: '', consentimento_lgpd: false, avisos_whatsapp: true })
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
          <span>Autorizo o Emprego Fácil a guardar o que eu falar para montar meu currículo e mostrar para empresas quando eu me candidatar. Meu endereço exato nunca é mostrado.</span>
        </label>
      )}
      {cand && (
        <label className="check">
          <input type="checkbox" checked={f.avisos_whatsapp} onChange={set('avisos_whatsapp')} />
          <span>Quero receber no WhatsApp avisos de vagas perto de casa e das minhas candidaturas.</span>
        </label>
      )}
      <Erro msg={erro} />
      <button className="grande" disabled={carregando}>{carregando ? 'Criando…' : 'Criar conta'}</button>
      <p className="quieto">Já tem conta? <Link to="/entrar">Entrar</Link></p>
    </form>
  )
}


export function Recuperar() {
  const { entrar } = useAuth()
  const nav = useNavigate()
  const [passo, setPasso] = useState(1)
  const [login, setLogin] = useState('')
  const [canal, setCanal] = useState('whatsapp')
  const [codigo, setCodigo] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')
  const [carregando, setCarregando] = useState(false)

  async function pedirCodigo(e) {
    e?.preventDefault(); setErro(''); setAviso(''); setCarregando(true)
    try {
      const r = await api('/api/auth/esqueci', { method: 'POST', body: { login } })
      setCanal(r.canal); setPasso(2)
      if (e === undefined) setAviso('Enviamos um código novo.')
    } catch (e2) { setErro(e2.message) } finally { setCarregando(false) }
  }

  async function redefinir(e) {
    e.preventDefault(); setErro(''); setCarregando(true)
    try {
      const data = await api('/api/auth/redefinir', { method: 'POST', body: { login, codigo, nova_senha: senha } })
      entrar(data); nav(homeDe(data.user.role))
    } catch (e2) { setErro(e2.message) } finally { setCarregando(false) }
  }

  if (passo === 1) return (
    <form className="form estreito" onSubmit={pedirCodigo}>
      <h1>Esqueci minha senha</h1>
      <p>Digite o celular (ou e-mail) da sua conta. Vamos mandar um código de 6 números.</p>
      <Campo label="Celular ou e-mail"><input value={login} onChange={(e) => setLogin(e.target.value)} inputMode="email" autoComplete="username" required /></Campo>
      <Erro msg={erro} />
      <button className="grande" disabled={carregando}>{carregando ? 'Enviando…' : 'Receber código'}</button>
      <p className="centro"><Link to="/entrar">Voltar para entrar</Link></p>
    </form>
  )

  return (
    <form className="form estreito" onSubmit={redefinir}>
      <h1>Crie uma senha nova</h1>
      <p className="caixa-destaque" style={{ margin: 0 }}>
        {canal === 'email' ? 'Se a conta existir, enviamos um código para o seu e-mail.' : 'Se a conta existir, enviamos um código para o seu WhatsApp.'} Ele vale por 15 minutos.
      </p>
      <Campo label="Código de 6 números">
        <input value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric"
          autoComplete="one-time-code" pattern="\d{6}" required style={{ fontSize: '1.4rem', letterSpacing: '.3em' }} />
      </Campo>
      <Campo label="Nova senha" dica="Pelo menos 4 números ou letras."><input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} minLength={4} required autoComplete="new-password" /></Campo>
      <Erro msg={erro} />{aviso && <p className="sucesso">{aviso}</p>}
      <button className="grande" disabled={carregando || codigo.length !== 6}>{carregando ? 'Salvando…' : 'Salvar nova senha'}</button>
      <p className="centro"><button type="button" className="link" onClick={() => pedirCodigo()} disabled={carregando}>Não chegou? Enviar de novo</button></p>
      <p className="quieto centro">Se você foi cadastrado por uma associação ou ONG, ela também pode gerar uma senha nova para você.</p>
    </form>
  )
}
