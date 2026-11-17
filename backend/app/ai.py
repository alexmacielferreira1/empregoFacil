"""Geração do currículo a partir das falas da entrevista.

Dois motores:
- IA (Claude via API da Anthropic), quando ANTHROPIC_API_KEY estiver definida;
- regras locais, sempre disponível e sem custo (fallback).

Regra de ouro dos dois: só usar o que a pessoa disse. Nada de inventar
empresa, data, curso ou habilidade.
"""
import json
import logging
import re

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

CATEGORIAS: dict[str, str] = {
    "limpeza": "Limpeza e conservação",
    "construcao": "Construção e reformas",
    "costura": "Costura e confecção",
    "cozinha": "Cozinha e alimentação",
    "cuidados": "Cuidado de pessoas",
    "comercio": "Comércio e atendimento",
    "logistica": "Logística, entregas e estoque",
    "beleza": "Beleza e estética",
    "manutencao": "Manutenção e serviços gerais",
    "jardinagem": "Jardinagem e paisagismo",
    "administrativo": "Administrativo e escritório",
    "outros": "Outros",
}

PERGUNTAS: list[dict[str, str]] = [
    {"id": "ultimo_trabalho", "texto": "Me conta sobre o último trabalho que você fez. O que você fazia no dia a dia?"},
    {"id": "tempo_local", "texto": "Quanto tempo você trabalhou nisso? E onde foi: em casa de família, empresa, por conta própria?"},
    {"id": "outros_trabalhos", "texto": "Você já fez outros trabalhos, mesmo bico ou sem carteira assinada? Pode contar todos."},
    {"id": "habilidades", "texto": "O que você sabe fazer bem? Pode ser qualquer coisa: cozinhar, consertar, cuidar de pessoas, vender, organizar."},
    {"id": "estudos", "texto": "Até que série você estudou? Já fez algum curso?"},
    {"id": "objetivo", "texto": "Que tipo de trabalho você procura agora? E em que dias e horários você pode trabalhar?"},
]

# palavra-chave -> (categoria, cargo profissional)
_MAPA: list[tuple[tuple[str, ...], str, str]] = [
    (("faxin", "diarista", "limpava", "limpeza", "limpar", "casa de família", "casa de familia", "doméstica", "domestica"),
     "limpeza", "Auxiliar de Limpeza"),
    (("azulej", "piso", "revestimento", "cerâmica", "ceramica", "porcelanato"), "construcao", "Assentador(a) de Revestimentos"),
    (("pedreiro", "obra", "servente", "reboco", "massa", "construção", "construcao", "tijolo"), "construcao", "Ajudante de Obras"),
    (("pint",), "construcao", "Pintor(a)"),
    (("eletric", "fiação", "fiacao", "tomada"), "manutencao", "Auxiliar de Eletricista"),
    (("encanad", "hidráulic", "hidraulic", "cano"), "manutencao", "Auxiliar de Encanador"),
    (("costur", "confecç", "confecc", "máquina de costura", "bainha", "roupa"), "costura", "Costureira(o)"),
    (("cozinh", "salgad", "marmita", "comida", "lanche", "restaurante", "padaria", "doce", "bolo"), "cozinha", "Auxiliar de Cozinha"),
    (("garçom", "garcom", "garçonete", "garconete"), "cozinha", "Garçom/Garçonete"),
    (("cuidador", "cuidava", "idoso", "idosa", "babá", "baba", "criança", "crianca", "acompanhante"), "cuidados", "Cuidador(a)"),
    (("vend", "loja", "caixa", "atend", "balcão", "balcao", "mercado"), "comercio", "Atendente / Vendedor(a)"),
    (("entreg", "motoboy", "moto", "bicicleta", "ifood"), "logistica", "Entregador(a)"),
    (("estoque", "depósito", "deposito", "carga", "descarga", "repositor", "armazém", "armazem"), "logistica", "Auxiliar de Estoque"),
    (("motorista", "dirig", "uber", "caminhão", "caminhao"), "logistica", "Motorista"),
    (("cabel", "manicure", "unha", "maquiag", "sobrancelha", "salão", "salao", "barbe"), "beleza", "Profissional de Beleza"),
    (("jardi", "grama", "poda", "planta"), "jardinagem", "Jardineiro(a)"),
    (("porteiro", "portaria", "zelador", "manutenção", "manutencao", "conserto", "consertava"), "manutencao", "Auxiliar de Manutenção"),
    (("escritório", "escritorio", "computador", "digita", "planilha", "recepç", "recepc", "telefone"), "administrativo", "Auxiliar Administrativo"),
]

_HABILIDADES: list[tuple[tuple[str, ...], str]] = [
    (("pontual", "horário", "horario", "nunca falt"), "Pontualidade e assiduidade"),
    (("organiz",), "Organização"),
    (("cozinh",), "Preparo de alimentos"),
    (("limp",), "Limpeza e higienização de ambientes"),
    (("cuid",), "Cuidado e atenção com pessoas"),
    (("vend", "convers", "atend"), "Bom atendimento ao público"),
    (("conserto", "consert"), "Pequenos reparos"),
    (("costur",), "Costura à mão e à máquina"),
    (("dirig", "motorista", "cnh", "carteira de motorista"), "Habilitação para dirigir"),
    (("computador", "celular", "whatsapp"), "Uso de celular e computador"),
    (("equipe", "grupo", "junto"), "Trabalho em equipe"),
    (("responsáv", "responsav", "confian"), "Responsabilidade e confiança"),
    (("força", "forca", "pesado", "braçal", "bracal"), "Disposição para trabalho físico"),
]


def _norm(t: str | None) -> str:
    return (t or "").strip()


def _frase(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip(" .,;")
    if not t:
        return ""
    return t[0].upper() + t[1:] + "."


def _pos(low: str, chaves: tuple[str, ...]) -> int | None:
    """Posição da primeira palavra que COMEÇA com alguma das chaves."""
    posicoes = [m.start() for k in chaves for m in [re.search(r"(?<!\w)" + re.escape(k), low)] if m]
    return min(posicoes) if posicoes else None


def _detectar(texto: str) -> list[tuple[str, str]]:
    """Funções citadas no texto, na ordem em que aparecem (a primeira citada é a principal)."""
    low = texto.lower()
    achados: list[tuple[int, str, str]] = []
    for chaves, cat, cargo in _MAPA:
        p = _pos(low, chaves)
        if p is not None and all(c != cargo for _, _, c in achados):
            achados.append((p, cat, cargo))
    return [(cat, cargo) for _, cat, cargo in sorted(achados)]


def _limpar_fala(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip(" .,;")
    return re.sub(r"^(eu|então|entao|bom|olha|é|e)\s+", "", t, flags=re.I)


def _tempo(texto: str) -> str | None:
    m = re.search(r"(\d+|um|uma|dois|duas|três|tres|quatro|cinco|seis|sete|oito|nove|dez)\s+(anos?|mes(es)?|meses)", texto.lower())
    return m.group(0) if m else None


def gerar_por_regras(nome: str, respostas: dict[str, str]) -> dict:
    ult = _norm(respostas.get("ultimo_trabalho"))
    tempo_local = _norm(respostas.get("tempo_local"))
    outros = _norm(respostas.get("outros_trabalhos"))
    hab = _norm(respostas.get("habilidades"))
    est = _norm(respostas.get("estudos"))
    obj = _norm(respostas.get("objetivo"))

    experiencias = []
    principal = _detectar(ult) or _detectar(tempo_local)
    if ult:
        periodo = _tempo(tempo_local) or _tempo(ult) or ""
        local = _limpar_fala(tempo_local)
        if periodo:  # "três anos no mercado do bairro" -> "No mercado do bairro"
            local = re.sub(re.escape(periodo), "", local, count=1, flags=re.I)
            local = re.sub(r"^[\s,]*(e\s+)?(foi\s+)?", "", local, flags=re.I)
        experiencias.append({
            "cargo": principal[0][1] if principal else "Experiência profissional",
            "periodo": periodo,
            "local": _frase(local) if len(local) > 2 else "",
            "descricao": _frase(_limpar_fala(ult)),
        })
    if outros and not re.fullmatch(r"(não|nao|nunca|nenhum)\.?", outros.lower()):
        for parte in re.split(r"[.;]|\btambém\b|\btambem\b|\be depois\b", outros):
            parte = parte.strip(" ,")
            if len(parte) < 4:
                continue
            det = _detectar(parte)
            experiencias.append({
                "cargo": det[0][1] if det else "Trabalho informal",
                "periodo": _tempo(parte) or "",
                "local": "",
                "descricao": _frase(_limpar_fala(parte)),
            })

    tudo = " ".join([ult, tempo_local, outros, hab, obj])
    categorias: list[str] = []
    for cat, _ in _detectar(tudo):
        if cat not in categorias:
            categorias.append(cat)

    tudo_low = tudo.lower()
    batidas = [(chaves, h) for chaves, h in _HABILIDADES if _pos(tudo_low, chaves) is not None]
    habilidades = [h for _, h in batidas]
    if hab:
        for item in re.split(r",|;|\be\b", hab):
            item = re.sub(r"^(eu\s+)?(sou|sei|gosto de|consigo)\s+", "", item.strip(" ."), flags=re.I)
            low = item.lower()
            ja_coberto = any(_pos(low, chaves) is not None for chaves, _ in batidas)
            if 3 <= len(item) <= 60 and not ja_coberto and low not in {h.lower() for h in habilidades}:
                habilidades.append(item[0].upper() + item[1:])
    habilidades = habilidades[:10]

    objetivo_cargos = _detectar(obj)
    if objetivo_cargos:
        objetivo = "Busco oportunidade como " + ", ".join(c for _, c in objetivo_cargos[:2]) + "."
    elif principal:
        objetivo = f"Busco oportunidade como {principal[0][1]} ou em áreas em que eu possa aprender."
    elif obj:
        objetivo = _frase(_limpar_fala(obj))
    else:
        objetivo = "Busco uma oportunidade de trabalho para crescer e aprender."

    if experiencias:
        cargos = list(dict.fromkeys(e["cargo"] for e in experiencias))
        resumo = f"Profissional com experiência prática como {', '.join(cargos[:3])}."
    else:
        resumo = "Pessoa dedicada, em busca da primeira oportunidade formal de trabalho."
    if habilidades:
        resumo += " Destaques: " + ", ".join(h.lower() for h in habilidades[:3]) + "."

    return {
        "nome": nome,
        "objetivo": objetivo,
        "resumo": resumo,
        "experiencias": experiencias,
        "habilidades": habilidades,
        "formacao": _frase(est) if est else "",
        "disponibilidade": _frase(obj) if obj else "",
        "categorias": categorias,
    }


_PROMPT = """Você ajuda pessoas de baixa renda a montar um currículo profissional a partir do que elas falaram numa entrevista por voz (transcrição, pode ter erros e gírias).

Regras:
- Use SOMENTE informações ditas pela pessoa. Não invente empresas, datas, cursos, certificações ou habilidades.
- Traduza a experiência informal para linguagem profissional e respeitosa (ex.: "limpava casa de família" -> "Auxiliar de Limpeza em residências").
- Trabalho sem carteira, bico e trabalho por conta própria contam como experiência.
- Texto curto, claro, em português do Brasil.
- "categorias": escolha entre {categorias}.

Nome: {nome}
Respostas da entrevista (JSON):
{respostas}

Responda APENAS com um JSON válido neste formato:
{{"nome": str, "objetivo": str, "resumo": str, "experiencias": [{{"cargo": str, "periodo": str, "local": str, "descricao": str}}], "habilidades": [str], "formacao": str, "disponibilidade": str, "categorias": [str]}}"""


def gerar_por_ia(nome: str, respostas: dict[str, str]) -> dict | None:
    s = get_settings()
    if not s.anthropic_api_key:
        return None
    prompt = _PROMPT.format(
        categorias=", ".join(CATEGORIAS.keys()), nome=nome, respostas=json.dumps(respostas, ensure_ascii=False)
    )
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": s.ai_model, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]},
            timeout=45,
        )
        r.raise_for_status()
        texto = "".join(b.get("text", "") for b in r.json().get("content", []))
        inicio, fim = texto.find("{"), texto.rfind("}")
        dados = json.loads(texto[inicio : fim + 1])
        dados["categorias"] = [c for c in dados.get("categorias", []) if c in CATEGORIAS]
        dados.setdefault("nome", nome)
        return dados
    except Exception as exc:  # noqa: BLE001 — qualquer falha cai no gerador por regras
        log.warning("IA indisponível, usando regras: %s", exc)
        return None


def gerar_curriculo(nome: str, respostas: dict[str, str]) -> tuple[dict, str]:
    dados = gerar_por_ia(nome, respostas)
    if dados:
        return dados, "ia"
    return gerar_por_regras(nome, respostas), "regras"
