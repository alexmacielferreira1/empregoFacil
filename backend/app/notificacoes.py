"""Envio de avisos e códigos por WhatsApp (e e-mail para empresas).

Provedores (variável WHATSAPP_PROVIDER):
- console: não envia nada, só escreve no log do servidor (padrão; bom para testar).
- meta:    WhatsApp Cloud API oficial. Mensagens iniciadas pela empresa exigem MODELOS
           aprovados no WhatsApp Manager (nomes em WHATSAPP_TPL_*).
- zapi:    Z-API (texto livre, sem modelo). Mais simples de começar, mas não é a API oficial.
"""
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import httpx
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.geo import distancia_km
from app.models import Application, CandidateProfile, Job, Notificacao, Resume, User

log = logging.getLogger("empregofacil.avisos")

SITUACOES = {
    "entrevista": "a empresa quer te chamar para entrevista",
    "contratado": "você foi contratado(a)!",
    "recusada": "a vaga seguiu com outra pessoa",
}


def telefone_e164(numero: str | None) -> str | None:
    """'51 98765-4321' -> '5551987654321'. Retorna None se não parecer celular brasileiro."""
    if not numero:
        return None
    dig = "".join(c for c in numero if c.isdigit())
    if dig.startswith("55") and len(dig) in (12, 13):
        return dig
    if len(dig) in (10, 11):
        return "55" + dig
    return None


# ---------- provedores ----------
def _meta(para: str, template: str, params: list[str], codigo: str | None = None) -> None:
    s = get_settings()
    if not (s.whatsapp_token and s.whatsapp_phone_number_id):
        raise RuntimeError("WHATSAPP_TOKEN/WHATSAPP_PHONE_NUMBER_ID não configurados")
    componentes = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
    if codigo:  # modelo de autenticação: o código vai no corpo E no botão "copiar código"
        componentes.append({"type": "button", "sub_type": "url", "index": "0",
                            "parameters": [{"type": "text", "text": codigo}]})
    r = httpx.post(
        f"https://graph.facebook.com/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {s.whatsapp_token}"},
        json={"messaging_product": "whatsapp", "to": para, "type": "template",
              "template": {"name": template, "language": {"code": s.whatsapp_idioma}, "components": componentes}},
        timeout=20,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Meta {r.status_code}: {r.text[:200]}")


def _zapi(para: str, texto: str) -> None:
    s = get_settings()
    if not (s.zapi_instance and s.zapi_token):
        raise RuntimeError("ZAPI_INSTANCE/ZAPI_TOKEN não configurados")
    headers = {"Client-Token": s.zapi_client_token} if s.zapi_client_token else {}
    r = httpx.post(f"https://api.z-api.io/instances/{s.zapi_instance}/token/{s.zapi_token}/send-text",
                   headers=headers, json={"phone": para, "message": texto}, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"Z-API {r.status_code}: {r.text[:200]}")


def enviar_whatsapp(db, *, user_id: int | None, telefone: str | None, tipo: str, texto: str, template: str,
                    params: list[str], resumo: str, codigo: str | None = None, referencia_id: int | None = None) -> bool:
    """Envia e registra. Nunca levanta erro: aviso que falha não pode derrubar a tela da pessoa."""
    s = get_settings()
    para = telefone_e164(telefone)
    if not para:
        return False
    provedor = (s.whatsapp_provider or "console").lower()
    status, erro = "enviado", None
    try:
        if provedor == "meta":
            _meta(para, template, params, codigo)
        elif provedor == "zapi":
            _zapi(para, texto)
        else:
            status = "simulado"
            log.warning("[WhatsApp simulado] para %s: %s", para, texto)
    except Exception as exc:  # noqa: BLE001
        status, erro = "falhou", str(exc)[:300]
        log.error("Falha no WhatsApp (%s) para %s: %s", provedor, para, exc)
    db.add(Notificacao(user_id=user_id, canal="whatsapp", tipo=tipo, destino=para, resumo=resumo[:300],
                       referencia_id=referencia_id, status=status, erro=erro))
    db.commit()
    return status != "falhou"


def enviar_email(db, *, user_id: int, para: str, assunto: str, texto: str, tipo: str, resumo: str) -> bool:
    s = get_settings()
    status, erro = "enviado", None
    try:
        if not s.smtp_host:
            status = "simulado"
            log.warning("[E-mail simulado] para %s: %s | %s", para, assunto, texto)
        else:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = s.smtp_from or s.smtp_user, para, assunto
            msg.set_content(texto)
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
                smtp.starttls()
                if s.smtp_user:
                    smtp.login(s.smtp_user, s.smtp_password or "")
                smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        status, erro = "falhou", str(exc)[:300]
        log.error("Falha no e-mail para %s: %s", para, exc)
    db.add(Notificacao(user_id=user_id, canal="email", tipo=tipo, destino=para, resumo=resumo[:300],
                       status=status, erro=erro))
    db.commit()
    return status != "falhou"


# ---------- casos de uso ----------
def enviar_codigo(db, user: User, codigo: str) -> str:
    """Manda o código de recuperação. Retorna o canal usado (whatsapp | email)."""
    s = get_settings()
    if "@" in user.login:
        enviar_email(db, user_id=user.id, para=user.login, tipo="codigo", resumo="Código de recuperação de senha",
                     assunto="Seu código do Emprego Fácil",
                     texto=f"Olá, {user.nome}!\n\nSeu código para criar uma nova senha é: {codigo}\n"
                           f"Ele vale por 15 minutos. Se não foi você, ignore esta mensagem.\n\n{s.app_url}")
        return "email"
    enviar_whatsapp(db, user_id=user.id, telefone=user.login, tipo="codigo", resumo="Código de recuperação de senha",
                    texto=f"Emprego Fácil: seu código para criar uma nova senha é {codigo}. Vale por 15 minutos. "
                          f"Não passe este código para ninguém.",
                    template=s.whatsapp_tpl_codigo, params=[codigo], codigo=codigo)
    return "whatsapp"


def _quer_avisos(prof: CandidateProfile | None) -> bool:
    return bool(prof and prof.avisos_whatsapp and prof.consentimento_lgpd and prof.telefone and prof.user.ativo)


def avisar_vaga_nova(job_id: int) -> int:
    """Avisa quem tem currículo na mesma área e mora perto. Roda em segundo plano. Retorna quantos avisou."""
    s = get_settings()
    enviados = 0
    with SessionLocal() as db:
        vaga = db.get(Job, job_id)
        if not vaga or vaga.status != "aberta" or vaga.exemplo:
            return 0
        desde = datetime.now(timezone.utc) - timedelta(days=1)
        perfis = db.scalars(select(CandidateProfile).join(Resume)).all()
        for prof in perfis:
            if not _quer_avisos(prof) or vaga.categoria not in (prof.resume.categorias or []):
                continue
            km = distancia_km(prof.lat, prof.lng, vaga.lat, vaga.lng)
            if km is None or km > s.aviso_raio_km:
                continue
            ja = db.scalar(select(func.count()).select_from(Notificacao).where(
                Notificacao.user_id == prof.user_id, Notificacao.tipo == "vaga_nova",
                Notificacao.referencia_id == vaga.id))
            hoje = db.scalar(select(func.count()).select_from(Notificacao).where(
                Notificacao.user_id == prof.user_id, Notificacao.tipo == "vaga_nova", Notificacao.created_at >= desde))
            if ja or hoje >= s.aviso_vagas_por_dia:
                continue
            primeiro = prof.user.nome.split(" ")[0]
            local = vaga.bairro or vaga.cidade
            link = f"{s.app_url}/vagas?vaga={vaga.id}"
            extra = " A empresa treina você." if vaga.com_treinamento else ""
            ok = enviar_whatsapp(
                db, user_id=prof.user_id, telefone=prof.telefone, tipo="vaga_nova", referencia_id=vaga.id,
                resumo=f"Vaga nova: {vaga.titulo} ({local})",
                texto=f"Olá, {primeiro}! Tem vaga nova perto de você no Emprego Fácil: {vaga.titulo}, em {local}.{extra} "
                      f"Veja e se candidate: {link}\n\nPara não receber mais avisos, desligue em Perfil.",
                template=s.whatsapp_tpl_vaga, params=[primeiro, vaga.titulo, local, link])
            enviados += int(ok)
    return enviados


def avisar_status(application_id: int) -> bool:
    s = get_settings()
    with SessionLocal() as db:
        a = db.get(Application, application_id)
        if not a or a.status not in SITUACOES:
            return False
        prof = a.candidate
        if not _quer_avisos(prof):
            return False
        ja = db.scalar(select(func.count()).select_from(Notificacao).where(
            Notificacao.tipo == "status", Notificacao.referencia_id == a.id, Notificacao.resumo.like(f"%[{a.status}]")))
        if ja:
            return False
        primeiro = prof.user.nome.split(" ")[0]
        situacao = SITUACOES[a.status]
        empresa = a.job.company.razao_social
        return enviar_whatsapp(
            db, user_id=prof.user_id, telefone=prof.telefone, tipo="status", referencia_id=a.id,
            resumo=f"{a.job.titulo} — {empresa} [{a.status}]",
            texto=f"Olá, {primeiro}! Novidade na sua candidatura para {a.job.titulo} ({empresa}): {situacao} "
                  f"Acompanhe em {s.app_url}/perfil",
            template=s.whatsapp_tpl_status, params=[primeiro, a.job.titulo, empresa, situacao])
