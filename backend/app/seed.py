"""Dados iniciais. Tudo marcado com exemplo=True é DEMONSTRAÇÃO, não é curso/vaga real."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.geo import coords
from app.models import CandidateProfile, Company, Course, Job, User
from app.security import hash_password

CURSOS = [
    ("Corte e costura básico", "Oficina comunitária (exemplo)", "costura", "presencial", 0, 40, "Lomba do Pinheiro", "Sábados, 9h às 12h"),
    ("Assentamento de pisos e azulejos", "Escola de ofícios (exemplo)", "construcao", "presencial", 49.9, 32, "Partenon", "Noites, seg a qui"),
    ("Auxiliar de cozinha e boas práticas", "Cozinha-escola (exemplo)", "cozinha", "presencial", 0, 24, "Centro Histórico", "Manhãs, 2 semanas"),
    ("Cuidador de idosos", "Associação de saúde (exemplo)", "cuidados", "online", 29.9, 60, None, "No seu ritmo"),
    ("Atendimento ao cliente e vendas", "Plataforma online (exemplo)", "comercio", "online", 0, 12, None, "No seu ritmo"),
    ("Limpeza profissional e produtos", "Cooperativa (exemplo)", "limpeza", "presencial", 0, 16, "Restinga", "Tardes, 1 semana"),
    ("Manicure e pedicure", "Salão-escola (exemplo)", "beleza", "presencial", 79.0, 40, "Sarandi", "Sábados"),
    ("Auxiliar de estoque e logística", "Centro de qualificação (exemplo)", "logistica", "presencial", 0, 20, "Navegantes", "Noites"),
    ("Pintura residencial", "Escola de ofícios (exemplo)", "construcao", "presencial", 0, 24, "Alvorada", "Sábados"),
    ("Informática básica e celular", "Biblioteca comunitária (exemplo)", "administrativo", "presencial", 0, 16, "Lomba do Pinheiro", "Terças e quintas, 14h"),
]

VAGAS = [
    ("Auxiliar de limpeza", "limpeza", "Limpeza de escritório e áreas comuns.", "R$ 1.650 + benefícios", "Seg a sex, 7h às 16h", "Centro Histórico",
     ["Vale-transporte", "Refeição no local", "Carteira assinada"], False, False, None, None, None),
    ("Ajudante de obras — treinamos você", "construcao", "Apoio em obra residencial; aprende assentamento de piso no trabalho.", "R$ 1.800", "Seg a sex, 7h30 às 17h", "Partenon",
     ["Vale-transporte", "Sem experiência", "Carteira assinada"], False, True, "junto", "Acompanhamento de um azulejista nas 4 primeiras semanas.", 1),
    ("Costureira", "costura", "Costura reta e overloque para confecção de uniformes.", "Por produção", "Seg a sex, 8h às 17h", "Lomba do Pinheiro",
     ["Perto de transporte", "Refeição no local"], True, False, None, None, None),
    ("Auxiliar de cozinha", "cozinha", "Pré-preparo e organização da cozinha de restaurante.", "R$ 1.700", "Turno da tarde", "Cidade Baixa",
     ["Refeição no local", "Vale-transporte", "Horário de meio turno"], False, True, "antes", "Curso de boas práticas antes de começar (gratuito).", 3),
    ("Repositor de mercado", "logistica", "Reposição de prateleiras e conferência de validade.", "R$ 1.620", "Escala 6x1", "Restinga",
     ["Vale-alimentação", "Carteira assinada", "Sem experiência"], False, False, None, None, None),
    ("Atendente de loja", "comercio", "Atendimento e caixa em loja de bairro.", "R$ 1.600 + comissão", "Seg a sáb, 9h às 18h", "Alvorada",
     ["Vale-transporte", "Uniforme"], False, True, "junto", "Treinamento de atendimento na primeira semana.", 5),
]


def seed(db: Session) -> None:
    s = get_settings()
    if not db.scalar(select(User).where(User.login == s.admin_login.lower())):
        db.add(User(login=s.admin_login.lower(), password_hash=hash_password(s.admin_password), role="admin", nome="Administrador"))
        db.commit()

    if not s.seed_demo or db.scalar(select(Course).where(Course.exemplo.is_(True))):
        return

    cursos = []
    for titulo, ofertante, cat, modo, preco, ch, bairro, horario in CURSOS:
        lat, lng = coords(bairro)
        c = Course(titulo=titulo, ofertante=ofertante, categoria=cat, modalidade=modo, preco=preco, carga_horaria=ch,
                   bairro=bairro, cidade="Porto Alegre" if bairro else None, lat=lat, lng=lng, horario=horario,
                   descricao="Curso de demonstração. Troque por cursos reais da sua região.", exemplo=True)
        db.add(c)
        cursos.append(c)
    db.flush()

    emp_user = User(login="empresa@demo.app", password_hash=hash_password("demo123"), role="empresa", nome="Empresa Demo")
    db.add(emp_user)
    db.flush()
    comp = Company(user_id=emp_user.id, razao_social="Empresa Demonstração Ltda", cidade="Porto Alegre", bairro="Centro Histórico", verificada=True)
    db.add(comp)
    db.flush()
    for titulo, cat, desc, sal, hor, bairro, vant, exp, trein, tipo, dtrein, curso_idx in VAGAS:
        lat, lng = coords(bairro)
        db.add(Job(company_id=comp.id, titulo=titulo, categoria=cat, descricao=desc, salario=sal, horario=hor, bairro=bairro,
                   lat=lat, lng=lng, vantagens=vant, exige_experiencia=exp, com_treinamento=trein, tipo_treinamento=tipo,
                   descricao_treinamento=dtrein, curso_id=cursos[curso_idx].id if curso_idx is not None else None, exemplo=True))

    cand = User(login="51999990000", password_hash=hash_password("demo123"), role="candidato", nome="Maria Demo")
    db.add(cand)
    db.flush()
    lat, lng = coords("Lomba do Pinheiro")
    db.add(CandidateProfile(user_id=cand.id, telefone="51999990000", bairro="Lomba do Pinheiro", lat=lat, lng=lng, consentimento_lgpd=True))

    db.add(User(login="parceiro@demo.app", password_hash=hash_password("demo123"), role="parceiro", nome="Associação Demo"))
    db.commit()
