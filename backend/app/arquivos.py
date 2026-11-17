"""Currículo enviado em arquivo: validação, leitura do texto e reorganização no modelo do Emprego Fácil.

Formatos: PDF, Word (.docx) e foto (JPG/PNG) de currículo em papel.
- Com IA (ANTHROPIC_API_KEY): o Claude lê o PDF/foto/texto e devolve o currículo organizado.
- Sem IA: extrai o texto de PDF/Word e separa as seções por regras. Foto sem IA não dá para ler.
"""
import base64
import io
import json
import logging
import re

import httpx
from fastapi import HTTPException

from app.ai import CATEGORIAS, _HABILIDADES, _detectar, _frase, _pos, _tempo
from app.config import get_settings

log = logging.getLogger(__name__)

TAMANHO_MAX = 5 * 1024 * 1024  # 5 MB
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TIPOS = {"pdf": "application/pdf", "docx": DOCX, "jpg": "image/jpeg", "png": "image/png"}


def identificar(nome: str, dados: bytes) -> str:
    """Confere o tipo pelo conteúdo (não só pela extensão). Retorna pdf | docx | jpg | png."""
    if not dados:
        raise HTTPException(422, "O arquivo está vazio.")
    if len(dados) > TAMANHO_MAX:
        raise HTTPException(413, "O arquivo passa de 5 MB. Envie um arquivo menor ou uma foto com menos qualidade.")
    if dados[:5] == b"%PDF-":
        return "pdf"
    if dados[:3] == b"\xff\xd8\xff":
        return "jpg"
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if dados[:2] == b"PK" and nome.lower().endswith(".docx"):
        return "docx"
    if nome.lower().endswith(".doc"):
        raise HTTPException(422, "Arquivos .doc antigos não são aceitos. No Word, use 'Salvar como' .docx ou PDF.")
    raise HTTPException(422, "Envie o currículo em PDF, Word (.docx) ou uma foto (JPG ou PNG).")


def extrair_texto(tipo: str, dados: bytes) -> str:
    try:
        if tipo == "pdf":
            from pypdf import PdfReader
            leitor = PdfReader(io.BytesIO(dados))
            return "\n".join((pg.extract_text() or "") for pg in leitor.pages[:6]).strip()
        if tipo == "docx":
            import docx
            doc = docx.Document(io.BytesIO(dados))
            linhas = [p.text for p in doc.paragraphs]
            for tabela in doc.tables:
                for linha in tabela.rows:
                    linhas.append(" | ".join(c.text for c in linha.cells))
            return "\n".join(linhas).strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao extrair texto (%s): %s", tipo, exc)
    return ""


# ---------- IA ----------
_PROMPT = """Abaixo está o currículo de uma pessoa (em arquivo ou texto). Organize-o no formato do Emprego Fácil.

Regras:
- Use SOMENTE informações que estão no currículo. Não invente empresas, datas, cursos ou habilidades.
- Pode reescrever em linguagem profissional, clara e respeitosa, em português do Brasil.
- Experiências mais recentes primeiro. Trabalho informal também conta.
- Se houver dados pessoais além de nome (CPF, RG, endereço completo, estado civil, foto), NÃO inclua.
- "categorias": áreas de trabalho que combinam com a pessoa, entre {categorias}.

Responda APENAS com JSON válido:
{{"nome": str, "objetivo": str, "resumo": str, "experiencias": [{{"cargo": str, "periodo": str, "local": str, "descricao": str}}], "habilidades": [str], "formacao": str, "disponibilidade": str, "categorias": [str]}}"""


def organizar_por_ia(nome: str, tipo: str, dados: bytes, texto: str) -> dict | None:
    s = get_settings()
    if not s.anthropic_api_key:
        return None
    prompt = _PROMPT.format(categorias=", ".join(CATEGORIAS.keys())) + f"\n\nNome no cadastro: {nome}"
    if tipo == "pdf":
        anexo = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                "data": base64.b64encode(dados).decode()}}
    elif tipo in ("jpg", "png"):
        anexo = {"type": "image", "source": {"type": "base64", "media_type": TIPOS[tipo],
                                             "data": base64.b64encode(dados).decode()}}
    else:
        anexo = {"type": "text", "text": f"Texto do currículo:\n{texto[:20000]}"}
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": s.ai_model, "max_tokens": 2000,
                  "messages": [{"role": "user", "content": [anexo, {"type": "text", "text": prompt}]}]},
            timeout=90,
        )
        r.raise_for_status()
        saida = "".join(b.get("text", "") for b in r.json().get("content", []))
        dados_cv = json.loads(saida[saida.find("{"): saida.rfind("}") + 1])
        dados_cv["categorias"] = [c for c in dados_cv.get("categorias", []) if c in CATEGORIAS]
        dados_cv["nome"] = dados_cv.get("nome") or nome
        return dados_cv
    except Exception as exc:  # noqa: BLE001
        log.warning("IA não conseguiu ler o currículo, usando regras: %s", exc)
        return None


# ---------- regras (sem IA) ----------
_SECOES = [
    ("objetivo", r"objetivo"),
    ("experiencias", r"experi[eê]ncia|hist[oó]rico profissional|trabalhos? anteriores|atua[cç][aã]o"),
    ("formacao", r"forma[cç][aã]o|escolaridade|educa[cç][aã]o|estudos|cursos?|qualifica[cç][aã]o"),
    ("habilidades", r"habilidades?|compet[eê]ncias?|conhecimentos?"),
    ("resumo", r"resumo|perfil|sobre mim|apresenta[cç][aã]o"),
    ("ignorar", r"dados pessoais|contato|refer[eê]ncias?|informa[cç][oõ]es (adicionais|pessoais)"),
]
_DADO_PESSOAL = re.compile(r"cpf|rg\b|\d{3}\.\d{3}\.\d{3}-\d{2}|estado civil|nacionalidade|nascimento|e-?mail|@|cep|telefone|celular|whats", re.I)


def organizar_por_regras(nome: str, texto: str) -> dict:
    secoes: dict[str, list[str]] = {k: [] for k, _ in _SECOES}
    secoes["solto"] = []
    atual = "solto"
    for linha in texto.splitlines():
        limpa = linha.strip(" •·-–—*\t")
        if not limpa:
            continue
        titulo = limpa.lower().rstrip(":")
        achou = next((k for k, rx in _SECOES if len(titulo) <= 40 and re.fullmatch(rf"({rx})[\w\s]*", titulo)), None)
        if achou:
            atual = achou
            continue
        if _DADO_PESSOAL.search(limpa):
            continue  # nunca copia CPF, endereço, contatos etc.
        secoes[atual].append(limpa)

    experiencias = []
    for item in secoes["experiencias"]:
        det = _detectar(item)
        if experiencias and not det and not _tempo(item) and len(item) > 25:
            experiencias[-1]["descricao"] = (experiencias[-1]["descricao"] + " " + _frase(item)).strip()
            continue
        experiencias.append({"cargo": det[0][1] if det else item[:60], "periodo": _tempo(item) or "",
                             "local": "", "descricao": _frase(item) if det or len(item) > 60 else ""})

    tudo = texto.lower()
    habilidades = list(dict.fromkeys(
        [h for chaves, h in _HABILIDADES if _pos(tudo, chaves) is not None]
        + [h for item in secoes["habilidades"] for h in re.split(r"[,;]", item) if 2 < len(h.strip()) <= 60]))
    habilidades = [h.strip()[0].upper() + h.strip()[1:] for h in habilidades][:12]

    categorias = list(dict.fromkeys(cat for cat, _ in _detectar(texto)))
    objetivo = " ".join(secoes["objetivo"]) or (f"Busco oportunidade como {experiencias[0]['cargo']}." if experiencias else "")
    resumo = " ".join(secoes["resumo"]) or " ".join(secoes["solto"][1:3])
    return {
        "nome": nome,
        "objetivo": _frase(objetivo) if objetivo else "",
        "resumo": _frase(resumo) if resumo else "",
        "experiencias": experiencias[:8],
        "habilidades": habilidades,
        "formacao": _frase(" ".join(secoes["formacao"])) if secoes["formacao"] else "",
        "disponibilidade": "",
        "categorias": categorias,
    }


def organizar(nome: str, tipo: str, dados: bytes) -> tuple[dict, str, str]:
    """Retorna (curriculo, motor, texto_extraido)."""
    texto = extrair_texto(tipo, dados)
    cv = organizar_por_ia(nome, tipo, dados, texto)
    if cv:
        return cv, "ia", texto
    if not texto or len(texto) < 30:
        if tipo in ("jpg", "png"):
            raise HTTPException(422, "Ainda não conseguimos ler fotos para atualizar o currículo. "
                                     "Escolha 'Usar do jeito que está' ou envie em PDF ou Word.")
        raise HTTPException(422, "Não conseguimos ler o texto deste arquivo (pode ser um PDF escaneado). "
                                 "Escolha 'Usar do jeito que está' ou faça o currículo por voz.")
    return organizar_por_regras(nome, texto), "regras", texto


def categorias_do_texto(texto: str) -> list[str]:
    return list(dict.fromkeys(cat for cat, _ in _detectar(texto or "")))
