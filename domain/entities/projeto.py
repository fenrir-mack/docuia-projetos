from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Projeto:
    id: Optional[int]
    nome: str
    descricao: str
    empresa_id: int
    status: str = "ativo"        # "ativo", "arquivado"
    categoria: str = ""
    link_repo: str = ""
    criado_em: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MembroProjeto:
    id: Optional[int]
    projeto_id: int
    usuario_id: int
    role: str = "member"         # "owner", "admin", "member"
    criado_em: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SolicitacaoProjeto:
    id: Optional[int]
    projeto_id: int
    usuario_id: int
    status: str = "pendente"     # "pendente", "aprovada", "recusada"
    criado_em: datetime = field(default_factory=datetime.utcnow)
