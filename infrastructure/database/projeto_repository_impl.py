from typing import List, Optional
from sqlalchemy.orm import Session

from domain.entities.projeto import Projeto, MembroProjeto, SolicitacaoProjeto
from domain.ports.projeto_repository import (
    IProjetoRepository, IMembroProjetoRepository, ISolicitacaoProjetoRepository
)
from infrastructure.database.models import ProjetoModel, MembroProjetoModel, SolicitacaoProjetoModel


class ProjetoRepositoryImpl(IProjetoRepository):

    def __init__(self, db: Session):
        self.db = db

    def _para_entidade(self, m: ProjetoModel) -> Projeto:
        return Projeto(
            id=m.id, nome=m.nome, descricao=m.descricao, 
            empresa_id=m.empresa_id, status=m.status, 
            criado_em=m.criado_em, cor=getattr(m, 'cor', 'teal')
        )

    def salvar(self, projeto: Projeto) -> Projeto:
        model = ProjetoModel(
            nome=projeto.nome, descricao=projeto.descricao, 
            empresa_id=projeto.empresa_id, cor=projeto.cor
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._para_entidade(model)

    def buscar_por_id(self, id: int) -> Optional[Projeto]:
        model = (
            self.db.query(ProjetoModel)
            .filter(ProjetoModel.id == id, ProjetoModel.status != "excluido")
            .first()
        )
        return self._para_entidade(model) if model else None

    def listar_por_usuario(self, usuario_id: int) -> List[Projeto]:
        membros = self.db.query(MembroProjetoModel).filter(MembroProjetoModel.usuario_id == usuario_id).all()
        projeto_ids = [m.projeto_id for m in membros]
        models = (
            self.db.query(ProjetoModel)
            .filter(ProjetoModel.id.in_(projeto_ids), ProjetoModel.status != "excluido")
            .all()
        )
        return [self._para_entidade(m) for m in models]

    def listar_por_empresa(self, empresa_id: int) -> List[Projeto]:
        models = (
            self.db.query(ProjetoModel)
            .filter(ProjetoModel.empresa_id == empresa_id, ProjetoModel.status != "excluido")
            .all()
        )
        return [self._para_entidade(m) for m in models]

    def atualizar(self, projeto: Projeto) -> Projeto:
        model = self.db.query(ProjetoModel).filter(ProjetoModel.id == projeto.id).first()
        model.nome = projeto.nome
        model.descricao = projeto.descricao
        model.status = projeto.status
        self.db.commit()
        self.db.refresh(model)
        return self._para_entidade(model)

    def deletar(self, id: int) -> None:
        model = self.db.query(ProjetoModel).filter(ProjetoModel.id == id).first()
        self.db.delete(model)
        self.db.commit()

    def ocultar_por_empresa(self, empresa_id: int) -> int:
        rows = (
            self.db.query(ProjetoModel)
            .filter(ProjetoModel.empresa_id == empresa_id, ProjetoModel.status != "excluido")
            .all()
        )
        for m in rows:
            m.status = "excluido"
        self.db.commit()
        return len(rows)


class MembroProjetoRepositoryImpl(IMembroProjetoRepository):

    def __init__(self, db: Session):
        self.db = db

    def _para_entidade(self, m: MembroProjetoModel) -> MembroProjeto:
        return MembroProjeto(
            id=m.id, projeto_id=m.projeto_id,
            usuario_id=m.usuario_id, role=m.role, criado_em=m.criado_em
        )

    def adicionar(self, membro: MembroProjeto) -> MembroProjeto:
        model = MembroProjetoModel(
            projeto_id=membro.projeto_id,
            usuario_id=membro.usuario_id, role=membro.role
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._para_entidade(model)

    def listar_por_projeto(self, projeto_id: int) -> List[MembroProjeto]:
        models = self.db.query(MembroProjetoModel).filter(MembroProjetoModel.projeto_id == projeto_id).all()
        return [self._para_entidade(m) for m in models]

    def buscar(self, projeto_id: int, usuario_id: int) -> Optional[MembroProjeto]:
        model = self.db.query(MembroProjetoModel).filter(
            MembroProjetoModel.projeto_id == projeto_id,
            MembroProjetoModel.usuario_id == usuario_id
        ).first()
        return self._para_entidade(model) if model else None

    def remover(self, projeto_id: int, usuario_id: int) -> None:
        model = self.db.query(MembroProjetoModel).filter(
            MembroProjetoModel.projeto_id == projeto_id,
            MembroProjetoModel.usuario_id == usuario_id
        ).first()
        if model:
            self.db.delete(model)
            self.db.commit()


class SolicitacaoProjetoRepositoryImpl(ISolicitacaoProjetoRepository):

    def __init__(self, db: Session):
        self.db = db

    def _para_entidade(self, m: SolicitacaoProjetoModel) -> SolicitacaoProjeto:
        return SolicitacaoProjeto(
            id=m.id, projeto_id=m.projeto_id,
            usuario_id=m.usuario_id, mensagem=getattr(m, 'mensagem', None), status=m.status, criado_em=m.criado_em
        )

    def salvar(self, solicitacao: SolicitacaoProjeto) -> SolicitacaoProjeto:
        model = SolicitacaoProjetoModel(
            projeto_id=solicitacao.projeto_id,
            usuario_id=solicitacao.usuario_id,
            mensagem=solicitacao.mensagem
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._para_entidade(model)

    def listar_por_projeto(self, projeto_id: int) -> List[SolicitacaoProjeto]:
        models = self.db.query(SolicitacaoProjetoModel).filter(
            SolicitacaoProjetoModel.projeto_id == projeto_id
        ).all()
        return [self._para_entidade(m) for m in models]

    def buscar_pendente(self, projeto_id: int, usuario_id: int) -> Optional[SolicitacaoProjeto]:
        model = (
            self.db.query(SolicitacaoProjetoModel)
            .filter(
                SolicitacaoProjetoModel.projeto_id == projeto_id,
                SolicitacaoProjetoModel.usuario_id == usuario_id,
                SolicitacaoProjetoModel.status == "pendente",
            )
            .order_by(SolicitacaoProjetoModel.id.desc())
            .first()
        )
        return self._para_entidade(model) if model else None

    def buscar_por_id(self, id: int) -> Optional[SolicitacaoProjeto]:
        model = self.db.query(SolicitacaoProjetoModel).filter(SolicitacaoProjetoModel.id == id).first()
        return self._para_entidade(model) if model else None

    def atualizar_status(self, id: int, status: str) -> SolicitacaoProjeto:
        model = self.db.query(SolicitacaoProjetoModel).filter(SolicitacaoProjetoModel.id == id).first()
        model.status = status
        self.db.commit()
        self.db.refresh(model)
        return self._para_entidade(model)
