from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.projeto import Projeto, MembroProjeto, SolicitacaoProjeto


class IProjetoRepository(ABC):
    @abstractmethod
    def salvar(self, projeto: Projeto) -> Projeto: pass

    @abstractmethod
    def buscar_por_id(self, id: int) -> Optional[Projeto]: pass

    @abstractmethod
    def listar_por_usuario(self, usuario_id: int) -> List[Projeto]: pass

    @abstractmethod
    def listar_por_empresa(self, empresa_id: int) -> List[Projeto]: pass

    @abstractmethod
    def atualizar(self, projeto: Projeto) -> Projeto: pass

    @abstractmethod
    def deletar(self, id: int) -> None: pass


class IMembroProjetoRepository(ABC):
    @abstractmethod
    def adicionar(self, membro: MembroProjeto) -> MembroProjeto: pass

    @abstractmethod
    def listar_por_projeto(self, projeto_id: int) -> List[MembroProjeto]: pass

    @abstractmethod
    def buscar(self, projeto_id: int, usuario_id: int) -> Optional[MembroProjeto]: pass

    @abstractmethod
    def remover(self, projeto_id: int, usuario_id: int) -> None: pass


class ISolicitacaoProjetoRepository(ABC):
    @abstractmethod
    def salvar(self, solicitacao: SolicitacaoProjeto) -> SolicitacaoProjeto: pass

    @abstractmethod
    def listar_por_projeto(self, projeto_id: int) -> List[SolicitacaoProjeto]: pass

    @abstractmethod
    def buscar_por_id(self, id: int) -> Optional[SolicitacaoProjeto]: pass

    @abstractmethod
    def atualizar_status(self, id: int, status: str) -> SolicitacaoProjeto: pass
