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
