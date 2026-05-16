from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class ProjetoModel(Base):
    __tablename__ = "projetos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(String(1000), default="")
    empresa_id = Column(Integer, nullable=False)
    status = Column(String(50), default="ativo")
    categoria = Column(String(255), default="")
    link_repo = Column(String(500), default="")
    criado_em = Column(DateTime, default=datetime.utcnow)


class MembroProjetoModel(Base):
    __tablename__ = "membros_projeto"

    id = Column(Integer, primary_key=True, index=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    usuario_id = Column(Integer, nullable=False)
    role = Column(String(50), default="member")
    criado_em = Column(DateTime, default=datetime.utcnow)


class SolicitacaoProjetoModel(Base):
    __tablename__ = "solicitacoes_projeto"

    id = Column(Integer, primary_key=True, index=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    usuario_id = Column(Integer, nullable=False)
    status = Column(String(50), default="pendente")
    criado_em = Column(DateTime, default=datetime.utcnow)
