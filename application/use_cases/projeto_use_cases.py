import random
from typing import List
from domain.entities.projeto import Projeto, MembroProjeto, SolicitacaoProjeto
from domain.ports.projeto_repository import (
    IProjetoRepository, IMembroProjetoRepository, ISolicitacaoProjetoRepository
)


class ListarProjetosUseCase:
    """Retorna todos os projetos em que o usuﾃ｡rio ﾃｩ membro."""

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

    def executar(self, nome: str, descricao: str, empresa_id: int, usuario_id: int) -> Projeto:
        cor = random.choice(['teal', 'rose', 'amber', 'indigo', 'emerald', 'cyan'])
        projeto = Projeto(
            id=None, nome=nome, descricao=descricao, 
            empresa_id=empresa_id, cor=cor
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

    def executar(self, projeto_id: int, nome: str, descricao: str, usuario_id: int) -> Projeto:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto nﾃ｣o encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Apenas donos ou admins podem editar o projeto")

        projeto.nome = nome
        projeto.descricao = descricao
        return self.repo.atualizar(projeto)


class ArquivarProjetoUseCase:
    """Muda o status do projeto para arquivado (apenas owner/admin)."""

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int) -> Projeto:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto nﾃ｣o encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Apenas donos ou admins podem arquivar o projeto")

        projeto.status = "arquivado"
        return self.repo.atualizar(projeto)


class DeletarProjetoUseCase:
    """Exclui (oculta) um projeto (apenas owner).

    Exclusﾃ｣o lﾃｳgica: muda o status para "excluido". A restauraﾃｧﾃ｣o ﾃｩ feita apenas
    via administraﾃｧﾃ｣o (ex.: alteraﾃｧﾃ｣o manual no banco).
    """

    def __init__(self, repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.repo = repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int) -> None:
        projeto = self.repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto nﾃ｣o encontrado")
            
        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro or membro.role != "owner":
            raise PermissionError("Apenas o dono pode excluir o projeto")
            
        projeto.status = "excluido"
        self.repo.atualizar(projeto)


class ListarMembrosProjetoUseCase:
    """Lista todos os membros de um projeto."""

    def __init__(self, membro_repo: IMembroProjetoRepository):
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int) -> List[MembroProjeto]:
        return self.membro_repo.listar_por_projeto(projeto_id)


class SolicitarAcessoProjetoUseCase:
    """Usuﾃ｡rio solicita entrada em um projeto."""

    def __init__(self, solicitacao_repo: ISolicitacaoProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.solicitacao_repo = solicitacao_repo
        self.membro_repo = membro_repo

    def executar(self, projeto_id: int, usuario_id: int, mensagem: str | None = None) -> SolicitacaoProjeto:
        ja_membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if ja_membro:
            raise ValueError("Você já é membro deste projeto")

        existente = self.solicitacao_repo.buscar_pendente(projeto_id, usuario_id)
        if existente:
            raise ValueError("Você já possui uma solicitação pendente para este projeto")

        solicitacao = SolicitacaoProjeto(id=None, projeto_id=projeto_id, usuario_id=usuario_id, mensagem=mensagem)
        return self.solicitacao_repo.salvar(solicitacao)


class GerenciarSolicitacaoProjetoUseCase:
    """Owner/Admin aprova ou recusa uma solicitaﾃｧﾃ｣o de acesso."""

    def __init__(
        self,
        solicitacao_repo: ISolicitacaoProjetoRepository,
        membro_repo: IMembroProjetoRepository
    ):
        self.solicitacao_repo = solicitacao_repo
        self.membro_repo = membro_repo

    def executar(self, solicitacao_id: int, acao: str, usuario_id_solicitante: int) -> SolicitacaoProjeto:
        if acao not in ("aprovada", "recusada"):
            raise ValueError("Aﾃｧﾃ｣o invﾃ｡lida. Use 'aprovada' ou 'recusada'")

        solicitacao = self.solicitacao_repo.buscar_por_id(solicitacao_id)
        if not solicitacao:
            raise ValueError("Solicitaﾃｧﾃ｣o nﾃ｣o encontrada")

        membro = self.membro_repo.buscar(solicitacao.projeto_id, usuario_id_solicitante)
        if not membro or membro.role not in ("owner", "admin"):
            raise PermissionError("Sem permissﾃ｣o para gerenciar solicitaﾃｧﾃｵes")

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


class SairProjetoUseCase:
    """Usuário remove a si mesmo do projeto.

    Regra: se for owner, só pode sair se existir pelo menos outro owner.
    """

    def __init__(self, membro_repo: IMembroProjetoRepository, projeto_repo: IProjetoRepository):
        self.membro_repo = membro_repo
        self.projeto_repo = projeto_repo

    def executar(self, projeto_id: int, usuario_id: int) -> None:
        projeto = self.projeto_repo.buscar_por_id(projeto_id)
        if not projeto:
            raise ValueError("Projeto nﾃ｣o encontrado")

        membro = self.membro_repo.buscar(projeto_id, usuario_id)
        if not membro:
            raise PermissionError("Sem acesso ao projeto")

        role = (membro.role or "").strip().lower()
        if role == "owner":
            membros = self.membro_repo.listar_por_projeto(projeto_id)
            outros_owners = [
                m for m in membros
                if int(m.usuario_id) != int(usuario_id) and (m.role or "").strip().lower() == "owner"
            ]
            if len(outros_owners) < 1:
                raise PermissionError("Para sair, o projeto precisa ter pelo menos 1 outro Owner.")

        self.membro_repo.remover(projeto_id, usuario_id)


class OcultarProjetosPorEmpresaUseCase:
    """Oculta (status=excluido) todos os projetos de uma empresa.

    Permissão: exige que o usuário seja owner/admin em pelo menos um projeto da empresa.
    """

    def __init__(self, projeto_repo: IProjetoRepository, membro_repo: IMembroProjetoRepository):
        self.projeto_repo = projeto_repo
        self.membro_repo = membro_repo

    def executar(self, empresa_id: int, usuario_id: int) -> int:
        projetos = self.projeto_repo.listar_por_empresa(empresa_id)
        if not projetos:
            return 0

        permitido = False
        for p in projetos:
            membro = self.membro_repo.buscar(p.id, usuario_id)
            if membro and (membro.role or "").strip().lower() in ("owner", "admin"):
                permitido = True
                break

        if not permitido:
            raise PermissionError("Sem permissão para ocultar projetos desta empresa")

        return self.projeto_repo.ocultar_por_empresa(empresa_id)

