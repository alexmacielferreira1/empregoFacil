# empregoFacil

Currículo por voz com IA, cursos grátis ou baratos e vagas perto de casa, para quem nunca fez currículo. Empresas publicam vagas e podem marcar **"treinamos você"**.

Stack (padrão da Base SaaS V1): **FastAPI + SQLAlchemy + PostgreSQL + Redis + React (Vite)**. Em produção é **um app só**: o FastAPI serve a API em `/api` e o React compilado em `/`.

## O que já funciona

| Área | Funcionalidades |
| --- | --- |
| Candidato | Cadastro por celular, entrevista guiada **por voz** (6 perguntas lidas em voz alta), currículo gerado e lido em voz alta, edição, PDF (imprimir), vagas ordenadas por "combina com você" + distância, candidatura com um toque, cursos sugeridos, acompanhamento das candidaturas |
| Empresa | Cadastro, publicar/editar vagas com vantagens, flag de treinamento (antes ou junto) e curso vinculado, ver candidatos com currículo, WhatsApp e distância, mudar status |
| Parceiro social (ONG, associação) | Cadastra pessoas que não conseguem sozinhas (com senha provisória) |
| Admin | Painel de números, usuários, CRUD de cursos |

**Voz:** o reconhecimento de fala usa o próprio navegador (Chrome do Android e Chrome/Edge no PC), sem custo. Onde não houver, a pessoa digita ou usa o microfone do teclado.

**IA:** com `ANTHROPIC_API_KEY` o currículo é escrito pelo Claude. Sem chave, um gerador por regras (grátis) traduz a experiência ("limpava casa de família" → "Auxiliar de Limpeza"). Os dois só usam o que a pessoa falou.

**Fotos dos cursos:** coloque em `frontend/public/img/cursos/` um `.jpg` por área (`costura.jpg`, `construcao.jpg`, `comercio.jpg`…; lista completa no `LEIA-ME.txt` da pasta) e rode o build. Sem foto, o card mostra o ícone da área. Cada curso também aceita foto própria (campo "Foto" no admin).

**Senha do admin:** vem da variável `ADMIN_PASSWORD`. Trocou a variável e reiniciou, a senha muda.

**Distância:** usa o centro aproximado de ~30 bairros/cidades da Grande Porto Alegre (`backend/app/geo.py`) ou a localização do celular, se a pessoa permitir.

## Recuperação de senha
- **Esqueci minha senha:** a pessoa recebe um código de 6 números no WhatsApp (contas de empresa: por e-mail). O código vale 15 minutos e é bloqueado após 5 erros. A tela sempre responde igual, exista a conta ou não.
- **Parceiro (ONG/associação):** gera senha nova para quem ele mesmo cadastrou.
- **Admin:** gera senha nova para qualquer usuário, menos o admin (a senha do admin vem de `ADMIN_PASSWORD`).
- O login tem limite de tentativas (10 por conta a cada 15 min).

## Avisos por WhatsApp
- **Vaga nova perto:** quando uma empresa publica (ou reabre) uma vaga, avisa quem tem currículo na mesma área e mora até `AVISO_RAIO_KM` (padrão 10 km). No máximo `AVISO_VAGAS_POR_DIA` avisos de vaga por pessoa por dia, e nunca a mesma vaga duas vezes.
- **Candidatura:** avisa quando a empresa chama para entrevista, contrata ou encerra.
- A pessoa liga/desliga os avisos no cadastro e no Perfil. O admin vê os últimos envios no Painel (telefone mascarado).
- Vagas de exemplo nunca geram aviso.

### Como ligar o envio de verdade
Sem configurar nada, `WHATSAPP_PROVIDER=console`: nada é enviado, as mensagens (e os códigos) aparecem só no **log do servidor**. Bom para testar.

**Opção A — API oficial do WhatsApp (Meta), recomendada para produção**
1. Em business.facebook.com, crie um app do tipo Business com o produto WhatsApp e cadastre um número.
2. Pegue o *token permanente* (usuário do sistema) e o *Phone number ID*.
3. No WhatsApp Manager, crie e aguarde aprovar 3 modelos em português (pt_BR):
   - `empregofacil_codigo` — categoria **Autenticação**, botão "copiar código".
   - `empregofacil_vaga_nova` — categoria Utilidade. Texto sugerido: `Olá, {{1}}! Tem vaga nova perto de você: {{2}}, em {{3}}. Veja e se candidate: {{4}}`
   - `empregofacil_status` — categoria Utilidade. Texto sugerido: `Olá, {{1}}! Novidade na sua candidatura para {{2}} ({{3}}): {{4}}`
4. Na ShardCloud: `WHATSAPP_PROVIDER=meta`, `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID`.

**Opção B — Z-API (mais rápido para testar, não é a API oficial)**
Crie uma instância em z-api.io, leia o QR Code com o WhatsApp do projeto e defina `WHATSAPP_PROVIDER=zapi`, `ZAPI_INSTANCE`, `ZAPI_TOKEN` e `ZAPI_CLIENT_TOKEN`. Use um número exclusivo do projeto: APIs não oficiais podem levar o número a ser bloqueado.

**E-mail (empresas):** preencha `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM`. Sem isso, o código das empresas também vai só para o log.

## Rodar no PC

### Com Docker (Postgres + Redis, igual à Base)
```bash
cp .env.example .env        # opcional
docker compose up --build
```
Web: http://localhost:5173 · API/docs: http://localhost:8000/docs

### Sem Docker (SQLite, mais rápido para testar)
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
set PORT=8000 && python main.py                      # Linux/Mac: PORT=8000 python main.py
```
Em outro terminal:
```bash
cd frontend && npm install && npm run dev
```

Testes: `cd backend && pip install pytest && python -m pytest -q`

### Usuários de demonstração (com `SEED_DEMO=true`)
| Tipo | Login | Senha |
| --- | --- | --- |
| Candidato | 51999990000 | demo123 |
| Empresa | empresa@demo.app | demo123 |
| Parceiro | parceiro@demo.app | demo123 |
| Admin | valor de `ADMIN_LOGIN` (padrão admin@empregofacil.app) | valor de `ADMIN_PASSWORD` (padrão admin123) |

Cursos e vagas de demonstração aparecem com o selo **Exemplo**.

## GitHub

Repositório: https://github.com/alexmacielferreira1/empregoFacil

Baixar no PC (primeira vez):
```bash
git clone https://github.com/alexmacielferreira1/empregoFacil.git
cd empregoFacil
```

Mandar alterações:
```bash
git add .
git commit -m "descreva o que mudou"
git push
```

Puxar alterações feitas em outro lugar:
```bash
git pull
```

O `backend/static` (React já compilado) vai junto de propósito, para a ShardCloud rodar sem precisar de Node. Depois de mudar o frontend, rode o build de novo antes do commit.

## Publicar na ShardCloud

1. Gere o pacote:
   - Windows: `powershell -ExecutionPolicy Bypass -File .\build.ps1`
   - Linux/Mac/Git Bash: `./build.sh`
   - Sai em `dist/empregofacil-shard.zip` (conteúdo da pasta `backend/` com `.shardcloud`, `main.py`, `requirements.txt` e `static/`).
2. No painel da ShardCloud, faça upload do zip (ou conecte a integração Git apontando para a pasta `backend/`).
3. Variáveis de ambiente mínimas: `SECRET_KEY` e `ADMIN_PASSWORD`. Recomendado: `DATABASE_URL` (Postgres da ShardCloud ou Neon). Opcional: `REDIS_URL` e `ANTHROPIC_API_KEY`.
4. Endereço: `https://empregofacil.shardweb.app` (campo `SUBDOMAIN` do `.shardcloud`).

`.shardcloud`:
```
DISPLAY_NAME=empregoFacil
MAIN=main.py
MEMORY=512
VERSION=recommended
SUBDOMAIN=empregofacil
```

**Porta:** o `main.py` escuta na variável `PORT` e, sem ela, na **80**. Se o painel mostrar outra porta, defina `PORT` nas variáveis de ambiente.

**Banco:** sem `DATABASE_URL` usa SQLite dentro do app. Serve para testar, mas os dados podem sumir a cada novo deploy. Para valer, use Postgres.

### Alternativa: kit gratuito (Render + Neon + Upstash)
O `backend/Dockerfile` roda direto no Render (porta 8000). Como o frontend já vai dentro do backend, a Vercel/Hostinger é opcional. Para separar, rode `npm run build` com `VITE_API_URL=https://empregofacil-api.onrender.com` e publique `backend/static`.

## Estrutura
```
backend/
  main.py            entrada (python main.py)
  .shardcloud        config da ShardCloud
  app/
    main.py          FastAPI + serve o React
    models.py        User, CandidateProfile, Resume, Company, Course, Job, Application
    ai.py            entrevista, gerador por IA e por regras
    geo.py           bairros/cidades e distância
    ratelimit.py     limite de gerações (Redis ou memória)
    seed.py          admin + dados de exemplo
    routers/         auth, candidates (+ parceiro), courses, jobs (+ empresa), admin
  tests/             fluxo completo candidato → empresa
frontend/            React + Vite (PWA)
```

## Próximos passos
- Alembic (migrações) no lugar do `create_all`
- Entrevista por áudio no WhatsApp
- Geocodificação por CEP e tempo de ônibus
- Ofertantes de curso se cadastrando sozinhos, selo de empresa que treina
- Verificação de CNPJ e denúncia de vaga
