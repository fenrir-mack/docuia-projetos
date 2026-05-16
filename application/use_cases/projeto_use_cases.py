from typing import List
from domain.entities.projeto import Projeto, MembroProjeto, SolicitacaoProjeto
from domain.ports.projeto_repository import (
    IProjetoRepository, IMembroProjetoRepository, ISolicitacaoProjetoRepository
)


class ListarProjetosUseCase:
    """Retorna todos os projetos em que o usuário é membro."""

    def __init__(self, repo: IProjetoRepository):
        self.repo = repo

    def executar(self, usuario_id: int) -> List[Projeto]:
        return self.repo.listar_por_usuario(usuario_id)

class ListarProjetosPorEmpresaUseCase:
    """Lista todos os projetos de uma empresa."""
    def __init__(self, repo: IProjetoRepository):
        self.repo = repo

    def executar(self, empresa_id: int) -> List[Projeto]:
        return self.repo.listar_por_empresa(empresa_id)


class CriarProjetoUseCase:
    """Cria um novo projeto e adiciona o criador como owner."""

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, nome: str, descricao: str, empresa_id: int, categoria: str, link_repo: str, usuario_id: int) -> Projeto:
        projeto = Projeto(
            id=None, nome=nome, descricao=descricao, 
            empresa_id=empresa_id, categoria=categoria, link_repo=link_repo
        )
        projeto = self.repo.salvar(projeto)

        # Criador vira owner do projeto
        membro = MembroProjeto(id=None, projeto_id=projeto.id, usuario_id=usuario_id, role="owner")
        self.membro_repo.adicionar(membro)

        return projeto


class EditarProjetoUseCase:
    """Edita dados do projeto (apenas owner/admin)."""

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, nome: str, descricao: str, categoria: str, link_repo: str, usuario_id: int) -> Projeto:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto não encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Apenas donos ou admins podem editar o projeto")

        projeto.nome = nome
        projeto.descricao = descricao
        projeto.categoria = categoria
        projeto.link_repo = link_repo
        return self.repo.atualizar(projeto)


class ArquivarProjetoUseCase:
    """Muda o status do projeto para arquivado (apenas owner/admin)."""

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int) -> Projeto:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto não encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Apenas donos ou admins podem arquivar o projeto")

        projeto.status = "arquivado"
        return self.repo.atualizar(projeto)


class DeletarProjetoUseCase:
    """Remove um projeto (apenas owner)."""

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int) -> None:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto não encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role != "owner":
            raise PermissionError("Apenas o dono pode excluir o projeto")
            
        self.repo.deletar(projeto_id)


class ListarMembrosProjetoUseCase:
    """Lista todos os membros de um projeto."""

    def __init__(self, membro_repo: IMembroProjetoRepository):
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int) -> List[MembroProjeto]:
        return self.membro_repo.listar_por_projeto(projeto_id)


class SolicitarAcessoProjetoUseCase:
    """Usuário solicita entrada em um projeto."""

    def __init__(self, solicitacao_repo: ISolicitacaoProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.solicitacao_repo = solicitacao_repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int) -> SolicitacaoProjeto:
        ja_membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if ja_membro:
            raise ValueError("Você já é membro deste projeto")

        solicitacao = SolicitacaoProjeto(id=None, projeto_id=projeto_id, usuario_id=usuario_id)
        return self.solicitacao_repo.salvar(solicitacao)


class GerenciarSolicitacaoProjetoUseCase:
    """Owner/Admin aprova ou recusa uma solicitação de acesso."""

    def __init__(
        self,
        solicitacao_repo: ISolicitacaoProjetoRepository,
        membro_repo: IMembroProjetoRepository
    ):
        self.solicitacao_repo = solicitacao_repo
        self.membro_repo = membro_repo

    def executar(self, solicitacao_id: int, acao: str, usuario_id_solicitante: int) -> SolicitacaoProjeto:
        if acao not in ("aprovada", "recusada"):
            raise ValueError("Ação inválida. Use 'aprovada' ou 'recusada'")

        solicitacao = self.solicitacao_repo.buscar_por_id(solicitacao_id)
        if not solicitacao:
            raise ValueError("Solicitação não encontrada")

        membro = self.membro_repo.buscar(solicitacao.projeto_id, usuario_id_solicitante)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Sem permissão para gerenciar solicitações")

        solicitacao = self.solicitacao_repo.atualizar_status(solicitacao_id, acao)

        if acao == "aprovada":
            novo_membro = MembroProjeto(
                id=None,
                projeto_id=solicitacao.projeto_id,
                usuario_id=solicitacao.usuario_id,
                role="member"
            )
            self.membro_repo.adicionar(novo_membro)

        return solicitacao
