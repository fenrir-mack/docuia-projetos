from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

from infrastructure.database.conexao import get_db
from infrastructure.database.projeto_repository_impl import (
    ProjetoRepositoryImpl, MembroProjetoRepositoryImpl, SolicitacaoProjetoRepositoryImpl
)
from application.use_cases.projeto_use_cases import (
    ListarProjetosUseCase, CriarProjetoUseCase, EditarProjetoUseCase,
    ArquivarProjetoUseCase, DeletarProjetoUseCase, ListarMembrosProjetoUseCase,
    SolicitarAcessoProjetoUseCase, GerenciarSolicitacaoProjetoUseCase, ListarProjetosPorEmpresaUseCase
)

router = APIRouter(prefix="/projetos", tags=["Projetos"])
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "docuia-secret-dev")


def get_usuario_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# --- Schemas ---

class ProjetoInput(BaseModel):
    nome: str
    descricao: str = ""
    empresa_id: int
    categoria: str = ""
    link_repo: str = ""

class ProjetoEditInput(BaseModel):
    nome: str
    descricao: str = ""
    categoria: str = ""
    link_repo: str = ""

class SolicitacaoAcaoInput(BaseModel):
    acao: str  # "aprovada" ou "recusada"


# --- Endpoints ---

@router.get("")
def listar_projetos(usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projetos = ListarProjetosUseCase(repo).executar(usuario_id)
    return [{"id": p.id, "nome": p.nome, "empresa_id": p.empresa_id, "status": p.status} for p in projetos]


@router.get("/empresa/{empresa_id}")
def listar_projetos_por_empresa(empresa_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projetos = ListarProjetosPorEmpresaUseCase(repo).executar(empresa_id)
    return [{"id": p.id, "nome": p.nome, "empresa_id": p.empresa_id, "status": p.status, "descricao": p.descricao} for p in projetos]

@router.post("", status_code=201)
def criar_projeto(dados: ProjetoInput, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    projeto = CriarProjetoUseCase(repo, membro_repo).executar(
        dados.nome, dados.descricao, dados.empresa_id, dados.categoria, dados.link_repo, usuario_id
    )
    return {"id": projeto.id, "nome": projeto.nome}


@router.get("/{projeto_id}")
def detalhe_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projeto = repo.buscar_por_id(projeto_id)
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return {
        "id": projeto.id, "nome": projeto.nome, "descricao": projeto.descricao,
        "empresa_id": projeto.empresa_id, "status": projeto.status,
        "categoria": projeto.categoria, "link_repo": projeto.link_repo
    }


@router.put("/{projeto_id}")
def editar_projeto(projeto_id: int, dados: ProjetoEditInput, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        projeto = EditarProjetoUseCase(repo, membro_repo).executar(
            projeto_id, dados.nome, dados.descricao, dados.categoria, dados.link_repo, usuario_id
        )
        return {"id": projeto.id, "nome": projeto.nome}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{projeto_id}/arquivar")
def arquivar_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        projeto = ArquivarProjetoUseCase(repo, membro_repo).executar(projeto_id, usuario_id)
        return {"id": projeto.id, "status": projeto.status}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{projeto_id}", status_code=204)
def deletar_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        DeletarProjetoUseCase(repo, membro_repo).executar(projeto_id, usuario_id)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{projeto_id}/membros")
def listar_membros(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    membro_repo = MembroProjetoRepositoryImpl(db)
    membros = ListarMembrosProjetoUseCase(membro_repo).executar(projeto_id)
    return [{"id": m.id, "usuario_id": m.usuario_id, "role": m.role} for m in membros]


@router.get("/{projeto_id}/solicitacoes")
def listar_solicitacoes(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    sol_repo = SolicitacaoProjetoRepositoryImpl(db)
    solicitacoes = sol_repo.listar_por_projeto(projeto_id)
    return [{"id": s.id, "usuario_id": s.usuario_id, "status": s.status} for s in solicitacoes]


@router.post("/{projeto_id}/solicitacoes", status_code=201)
def solicitar_acesso(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    sol_repo = SolicitacaoProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        sol = SolicitarAcessoProjetoUseCase(sol_repo, membro_repo).executar(projeto_id, usuario_id)
        return {"id": sol.id, "status": sol.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{projeto_id}/solicitacoes/{solicitacao_id}")
def gerenciar_solicitacao(projeto_id: int, solicitacao_id: int, dados: SolicitacaoAcaoInput, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    sol_repo = SolicitacaoProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        sol = GerenciarSolicitacaoProjetoUseCase(sol_repo, membro_repo).executar(
            solicitacao_id, dados.acao, usuario_id
        )
        return {"id": sol.id, "status": sol.status}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))
