import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai import gerar_por_regras  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_regras_traduz_experiencia_informal():
    cv = gerar_por_regras("Marli", {
        "ultimo_trabalho": "eu limpava casa de família e passava roupa",
        "tempo_local": "dez anos, na casa de uma família no Menino Deus",
        "outros_trabalhos": "fazia salgados pra vender",
        "habilidades": "sou organizada e pontual, costuro bem",
        "objetivo": "quero trabalhar de costureira de manhã",
    })
    assert cv["experiencias"][0]["cargo"] == "Auxiliar de Limpeza"
    assert cv["experiencias"][0]["periodo"] == "dez anos"
    assert "costura" in cv["categorias"] and "limpeza" in cv["categorias"]
    assert "Costureira(o)" in cv["objetivo"]


def test_fluxo_completo(client):
    # candidato se cadastra
    r = client.post("/api/auth/register", json={
        "nome": "Joana Teste", "login": "(51) 98888-7777", "senha": "1234", "role": "candidato",
        "bairro": "Partenon", "consentimento_lgpd": True})
    assert r.status_code == 201, r.text
    tok = r.json()["access_token"]
    assert r.json()["user"]["login"] == "51988887777"

    # sem currículo não pode se candidatar
    vagas = client.get("/api/candidato/vagas", headers=auth(tok)).json()
    assert vagas and vagas[0]["distancia_km"] is not None
    assert client.post(f"/api/vagas/{vagas[0]['id']}/candidatar", headers=auth(tok)).status_code == 422

    # entrevista por voz -> currículo
    perguntas = client.get("/api/candidato/entrevista/perguntas", headers=auth(tok)).json()
    assert len(perguntas) == 6
    r = client.post("/api/candidato/curriculo/gerar", headers=auth(tok), json={"respostas": {
        "ultimo_trabalho": "trabalhei de servente de obra, carregava massa e tijolo",
        "tempo_local": "dois anos numa construtora",
        "objetivo": "quero aprender a colocar piso e azulejo"}})
    assert r.status_code == 200, r.text
    cv = r.json()
    assert cv["gerado_por"] == "regras" and "construcao" in cv["categorias"]

    # vaga de construção com treinamento aparece primeiro (combina + perto)
    vagas = client.get("/api/candidato/vagas", headers=auth(tok)).json()
    assert vagas[0]["combina"] is True and vagas[0]["com_treinamento"] is True
    assert vagas[0]["curso"] is not None

    r = client.post(f"/api/vagas/{vagas[0]['id']}/candidatar", headers=auth(tok), json={"mensagem": "Tenho interesse"})
    assert r.status_code == 201
    assert client.post(f"/api/vagas/{vagas[0]['id']}/candidatar", headers=auth(tok)).status_code == 409
    assert len(client.get("/api/candidato/candidaturas", headers=auth(tok)).json()) == 1

    sugeridos = client.get("/api/candidato/cursos-sugeridos", headers=auth(tok)).json()
    assert sugeridos and sugeridos[0]["categoria"] == "construcao"

    # empresa demo vê o candidato, sem endereço exato
    emp = client.post("/api/auth/login", json={"login": "empresa@demo.app", "senha": "demo123"}).json()["access_token"]
    minhas = client.get("/api/empresa/vagas", headers=auth(emp)).json()
    alvo = next(v for v in minhas if v["id"] == vagas[0]["id"])
    assert alvo["total_candidatos"] == 1
    cands = client.get(f"/api/empresa/vagas/{alvo['id']}/candidatos", headers=auth(emp)).json()
    assert cands[0]["nome"] == "Joana Teste" and cands[0]["bairro"] == "Partenon" and cands[0]["curriculo"]
    r = client.put(f"/api/empresa/candidaturas/{cands[0]['application_id']}", headers=auth(emp), json={"status": "entrevista"})
    assert r.json()["status"] == "entrevista"

    # empresa cria vaga nova
    r = client.post("/api/empresa/vagas", headers=auth(emp), json={
        "titulo": "Pintor", "categoria": "construcao", "descricao": "Pintura de apartamentos",
        "bairro": "Glória", "com_treinamento": True, "tipo_treinamento": "antes"})
    assert r.status_code == 201 and r.json()["bairro"] == "Glória"

    # candidato não acessa área de empresa
    assert client.get("/api/empresa/vagas", headers=auth(tok)).status_code == 403


def test_parceiro_cadastra_por_alguem(client):
    p = client.post("/api/auth/login", json={"login": "parceiro@demo.app", "senha": "demo123"}).json()["access_token"]
    r = client.post("/api/parceiro/candidatos", headers=auth(p), json={
        "nome": "Seu José", "login": "51977776666", "bairro": "Restinga", "consentimento_lgpd": True})
    assert r.status_code == 201
    senha = r.json()["senha_provisoria"]
    assert client.post("/api/auth/login", json={"login": "51977776666", "senha": senha}).status_code == 200
    assert client.get("/api/parceiro/candidatos", headers=auth(p)).json()[0]["nome"] == "Seu José"


def test_admin_resumo(client):
    adm = client.post("/api/auth/login", json={"login": "admin@empregofacil.app", "senha": "admin123"}).json()["access_token"]
    r = client.get("/api/admin/resumo", headers=auth(adm)).json()
    assert r["cursos"] >= 10 and r["candidaturas"] >= 1


def test_spa_e_api_404(client):
    assert client.get("/api/nao-existe").status_code == 404
    assert client.get("/qualquer/rota").status_code == 200


# ---------- recuperação de senha ----------
def test_recuperar_senha(client, monkeypatch):
    import app.routers.auth as auth_mod
    enviados = {}
    monkeypatch.setattr(auth_mod, "enviar_codigo", lambda db, user, codigo: enviados.update({user.login: codigo}) or "whatsapp")

    # conta inexistente: mesma resposta, nada enviado
    r = client.post("/api/auth/esqueci", json={"login": "51900000000"})
    assert r.status_code == 200 and "51900000000" not in enviados

    r = client.post("/api/auth/esqueci", json={"login": "(51) 98888-7777"})
    assert r.status_code == 200 and r.json()["canal"] == "whatsapp"
    codigo = enviados["51988887777"]
    errado = "000000" if codigo != "000000" else "111111"
    r = client.post("/api/auth/redefinir", json={"login": "51988887777", "codigo": errado, "nova_senha": "nova1"})
    assert r.status_code == 400 and "4 tentativa" in r.json()["detail"]
    r = client.post("/api/auth/redefinir", json={"login": "51988887777", "codigo": codigo, "nova_senha": "nova1"})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/api/auth/login", json={"login": "51988887777", "senha": "nova1"}).status_code == 200
    # código já usado não vale de novo
    assert client.post("/api/auth/redefinir", json={"login": "51988887777", "codigo": codigo, "nova_senha": "x1234"}).status_code == 400


def test_codigo_bloqueia_apos_5_erros(client, monkeypatch):
    import app.routers.auth as auth_mod
    enviados = {}
    monkeypatch.setattr(auth_mod, "enviar_codigo", lambda db, user, codigo: enviados.update({user.login: codigo}) or "whatsapp")
    client.post("/api/auth/esqueci", json={"login": "51977776666"})
    codigo = enviados["51977776666"]
    errado = "000000" if codigo != "000000" else "111111"
    for _ in range(5):
        client.post("/api/auth/redefinir", json={"login": "51977776666", "codigo": errado, "nova_senha": "abcd"})
    r = client.post("/api/auth/redefinir", json={"login": "51977776666", "codigo": codigo, "nova_senha": "abcd"})
    assert r.status_code == 400  # bloqueado mesmo com o código certo


def test_parceiro_e_admin_geram_senha_nova(client):
    p = client.post("/api/auth/login", json={"login": "parceiro@demo.app", "senha": "demo123"}).json()["access_token"]
    pessoa = client.get("/api/parceiro/candidatos", headers=auth(p)).json()[0]
    r = client.post(f"/api/parceiro/candidatos/{pessoa['id']}/nova-senha", headers=auth(p))
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"login": pessoa["login"], "senha": r.json()["senha_provisoria"]}).status_code == 200
    # parceiro não mexe em quem não cadastrou
    outro = client.post("/api/auth/register", json={"nome": "Outra Pessoa", "login": "51966665555", "senha": "1234",
                                                    "role": "candidato", "consentimento_lgpd": True}).json()["user"]["id"]
    assert client.post(f"/api/parceiro/candidatos/{outro}/nova-senha", headers=auth(p)).status_code == 404
    adm = client.post("/api/auth/login", json={"login": "admin@empregofacil.app", "senha": "admin123"}).json()["access_token"]
    assert client.post(f"/api/admin/usuarios/{outro}/nova-senha", headers=auth(adm)).status_code == 200


# ---------- avisos por WhatsApp ----------
def test_avisos_vaga_nova_e_status(client):
    from app.database import SessionLocal
    from app.models import Notificacao
    from app.notificacoes import telefone_e164
    assert telefone_e164("(51) 98765-4321") == "5551987654321"
    assert telefone_e164("5551987654321") == "5551987654321"
    assert telefone_e164("123") is None

    emp = client.post("/api/auth/login", json={"login": "empresa@demo.app", "senha": "demo123"}).json()["access_token"]
    # Joana (Partenon, área construção) deve ser avisada de vaga de construção na Glória (~3 km)
    r = client.post("/api/empresa/vagas", headers=auth(emp), json={
        "titulo": "Assentador de piso", "categoria": "construcao", "descricao": "Obra residencial", "bairro": "Glória"})
    vaga_id = r.json()["id"]
    with SessionLocal() as db:
        avisos = db.query(Notificacao).filter_by(tipo="vaga_nova", referencia_id=vaga_id).all()
        assert len(avisos) == 1 and avisos[0].destino == "5551988887777" and avisos[0].status == "simulado"
    # vaga longe (Novo Hamburgo) não avisa
    r = client.post("/api/empresa/vagas", headers=auth(emp), json={
        "titulo": "Servente", "categoria": "construcao", "descricao": "Obra", "bairro": "Novo Hamburgo"})
    with SessionLocal() as db:
        assert db.query(Notificacao).filter_by(tipo="vaga_nova", referencia_id=r.json()["id"]).count() == 0

    # mudança de status avisa a candidata
    vagas = client.get("/api/empresa/vagas", headers=auth(emp)).json()
    alvo = next(v for v in vagas if v["total_candidatos"])
    cand = client.get(f"/api/empresa/vagas/{alvo['id']}/candidatos", headers=auth(emp)).json()[0]
    client.put(f"/api/empresa/candidaturas/{cand['application_id']}", headers=auth(emp), json={"status": "contratado"})
    with SessionLocal() as db:
        resumos = [n.resumo for n in db.query(Notificacao).filter_by(tipo="status", referencia_id=cand["application_id"])]
        assert any(r.endswith("[entrevista]") for r in resumos) and any(r.endswith("[contratado]") for r in resumos)

    # quem desliga os avisos não recebe
    tok = client.post("/api/auth/login", json={"login": "51988887777", "senha": "nova1"}).json()["access_token"]
    assert client.put("/api/candidato/perfil", headers=auth(tok), json={"avisos_whatsapp": False}).json()["avisos_whatsapp"] is False
    r = client.post("/api/empresa/vagas", headers=auth(emp), json={
        "titulo": "Pedreiro", "categoria": "construcao", "descricao": "Obra", "bairro": "Partenon"})
    with SessionLocal() as db:
        assert db.query(Notificacao).filter_by(tipo="vaga_nova", referencia_id=r.json()["id"]).count() == 0

    adm = client.post("/api/auth/login", json={"login": "admin@empregofacil.app", "senha": "admin123"}).json()["access_token"]
    lista = client.get("/api/admin/avisos", headers=auth(adm)).json()
    assert lista and all(a["destino"].endswith("****") for a in lista)


# ---------- currículo pronto (arquivo) ----------
def _pdf_curriculo() -> bytes:
    import io
    from reportlab.pdfgen import canvas
    buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
    for linha in ["Carlos Souza", "CPF 123.456.789-00", "Rua das Flores, 10 - CEP 91000-000",
                  "OBJETIVO", "Trabalhar como auxiliar de cozinha",
                  "EXPERIÊNCIA", "Auxiliar de cozinha - Restaurante Bom Sabor (2 anos)",
                  "Preparo de saladas, organização do estoque e limpeza da cozinha.",
                  "Garçom - Lancheria do Centro (1 ano)",
                  "FORMAÇÃO", "Ensino médio completo", "HABILIDADES", "Pontual, trabalho em equipe, organizado"]:
        c.drawString(50, y, linha); y -= 22
    c.save(); return buf.getvalue()


def _docx_curriculo() -> bytes:
    import io
    import docx
    d = docx.Document()
    for linha in ["Joana Lima", "Experiência", "Costureira em confecção - 3 anos", "Formação", "Curso de corte e costura"]:
        d.add_paragraph(linha)
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


def _novo_candidato(client, fone):
    r = client.post("/api/auth/register", json={"nome": "Teste Arquivo", "login": fone, "senha": "1234",
                                                "role": "candidato", "bairro": "Centro Histórico", "consentimento_lgpd": True})
    return r.json()["access_token"]


def test_enviar_pdf_e_atualizar(client):
    tok = _novo_candidato(client, "51955550001")
    r = client.post("/api/candidato/curriculo/arquivo", headers=auth(tok), data={"modo": "atualizar"},
                    files={"arquivo": ("curriculo.pdf", _pdf_curriculo(), "application/pdf")})
    assert r.status_code == 200, r.text
    cv = r.json()
    assert cv["origem"] == "arquivo_atualizado" and cv["usar_arquivo"] is False and cv["confirmado"] is False
    assert "cozinha" in cv["categorias"]
    c = cv["conteudo"]
    assert c["experiencias"][0]["cargo"] == "Auxiliar de Cozinha"
    assert "médio" in c["formacao"].lower()
    texto = str(c)
    assert "123.456.789" not in texto and "Rua das Flores" not in texto  # dados pessoais não são copiados
    baixado = client.get("/api/candidato/curriculo/arquivo", headers=auth(tok))
    assert baixado.status_code == 200 and baixado.content[:5] == b"%PDF-"


def test_usar_docx_como_esta_e_empresa_baixa(client):
    tok = _novo_candidato(client, "51955550002")
    r = client.post("/api/candidato/curriculo/arquivo", headers=auth(tok), data={"modo": "usar", "categorias": "limpeza"},
                    files={"arquivo": ("meu cv.docx", _docx_curriculo(), "application/octet-stream")})
    assert r.status_code == 200, r.text
    cv = r.json()
    assert cv["usar_arquivo"] is True and cv["confirmado"] is True
    assert set(cv["categorias"]) >= {"limpeza", "costura"}  # escolhida + detectada no texto
    # pode se candidatar com o arquivo
    vaga = client.get("/api/candidato/vagas", headers=auth(tok)).json()[0]
    assert client.post(f"/api/vagas/{vaga['id']}/candidatar", headers=auth(tok)).status_code == 201
    emp = client.post("/api/auth/login", json={"login": "empresa@demo.app", "senha": "demo123"}).json()["access_token"]
    cand = next(c for c in client.get(f"/api/empresa/vagas/{vaga['id']}/candidatos", headers=auth(emp)).json()
                if c["nome"] == "Teste Arquivo")
    assert cand["usar_arquivo"] is True and cand["arquivo_nome"] == "meu cv.docx"
    arq = client.get(f"/api/empresa/candidaturas/{cand['application_id']}/arquivo", headers=auth(emp))
    assert arq.status_code == 200 and arq.content[:2] == b"PK"
    # outra empresa / candidato não baixa
    assert client.get(f"/api/empresa/candidaturas/{cand['application_id']}/arquivo", headers=auth(tok)).status_code == 403
    # depois pede para melhorar o mesmo arquivo
    r = client.post("/api/candidato/curriculo/arquivo/atualizar", headers=auth(tok))
    assert r.status_code == 200 and r.json()["origem"] == "arquivo_atualizado"
    assert r.json()["conteudo"]["experiencias"][0]["cargo"] == "Costureira(o)"
    # e volta a mandar o arquivo original
    assert client.put("/api/candidato/curriculo/modo?usar_arquivo=true", headers=auth(tok)).json()["usar_arquivo"] is True


def test_arquivo_invalido_e_apagar(client):
    tok = _novo_candidato(client, "51955550003")
    enviar = lambda nome, dados, modo="usar", cats="limpeza": client.post(
        "/api/candidato/curriculo/arquivo", headers=auth(tok), data={"modo": modo, "categorias": cats},
        files={"arquivo": (nome, dados, "application/octet-stream")})
    assert enviar("virus.exe", b"MZ\x90\x00").status_code == 422
    assert enviar("antigo.doc", b"\xd0\xcf\x11\xe0").status_code == 422
    assert enviar("grande.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024)).status_code == 413
    foto = b"\xff\xd8\xff\xe0" + b"0" * 100
    assert enviar("foto.jpg", foto, modo="atualizar").status_code == 422  # sem IA não lê foto
    assert enviar("foto.jpg", foto, cats="").status_code == 422          # usar sem área
    assert enviar("foto.jpg", foto).status_code == 200                    # usar com área: ok
    r = client.delete("/api/candidato/curriculo/arquivo", headers=auth(tok))
    assert r.status_code == 200 and r.json() is None  # só existia o arquivo: currículo apagado
    assert client.get("/api/candidato/curriculo", headers=auth(tok)).json() is None
