from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

from infrastructure.database.conexao import get_db
from infrastructure.database.models import AcessoProjetoModel, ProjetoModel
from infrastructure.database.projeto_repository_impl import (
    ProjetoRepositoryImpl, MembroProjetoRepositoryImpl, SolicitacaoProjetoRepositoryImpl
)
from application.use_cases.projeto_use_cases import (
    ListarProjetosUseCase, CriarProjetoUseCase, EditarProjetoUseCase,
    ArquivarProjetoUseCase, DeletarProjetoUseCase, ListarMembrosProjetoUseCase,
    SolicitarAcessoProjetoUseCase, GerenciarSolicitacaoProjetoUseCase, ListarProjetosPorEmpresaUseCase, SairProjetoUseCase,
    OcultarProjetosPorEmpresaUseCase
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

class ProjetoEditInput(BaseModel):
    nome: str
    descricao: str = ""

class SolicitarAcessoInput(BaseModel):
    mensagem: str | None = None

class SolicitacaoAcaoInput(BaseModel):
    acao: str  # "aprovada" ou "recusada"

class PapelProjetoOut(BaseModel):
    nome: str
    descricao: str = ""
    permissoes: str = ""

# --- Endpoints ---

@router.get("")
def listar_projetos(usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projetos = ListarProjetosUseCase(repo).executar(usuario_id)
    return [{"id": p.id, "nome": p.nome, "empresa_id": p.empresa_id, "status": p.status, "cor": getattr(p, "cor", "teal")} for p in projetos]


@router.post("/{projeto_id:int}/acessos", status_code=204)
def registrar_acesso_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    existing = (
        db.query(AcessoProjetoModel)
        .filter(AcessoProjetoModel.projeto_id == projeto_id, AcessoProjetoModel.usuario_id == usuario_id)
        .first()
    )
    now = datetime.utcnow()
    if existing:
        existing.ultimo_acesso_em = now
    else:
        db.add(AcessoProjetoModel(projeto_id=projeto_id, usuario_id=usuario_id, ultimo_acesso_em=now))
    db.commit()


@router.get("/recentes")
def listar_projetos_recentes(limit: int = 6, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 50))
    rows = (
        db.query(ProjetoModel, AcessoProjetoModel.ultimo_acesso_em)
        .join(AcessoProjetoModel, AcessoProjetoModel.projeto_id == ProjetoModel.id)
        .filter(AcessoProjetoModel.usuario_id == usuario_id)
        .order_by(AcessoProjetoModel.ultimo_acesso_em.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "empresa_id": p.empresa_id,
            "status": p.status,
            "cor": getattr(p, "cor", "teal"),
            "ultimo_acesso_em": ts.isoformat() if ts else None,
        }
        for (p, ts) in rows
    ]

@router.get("/empresa/{empresa_id:int}")
def listar_projetos_por_empresa(empresa_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projetos = ListarProjetosPorEmpresaUseCase(repo).executar(empresa_id)
    return [{"id": p.id, "nome": p.nome, "empresa_id": p.empresa_id, "status": p.status, "descricao": p.descricao, "cor": getattr(p, "cor", "teal")} for p in projetos]

@router.post("", status_code=201)
def criar_projeto(dados: ProjetoInput, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    projeto = CriarProjetoUseCase(repo, membro_repo).executar(
        dados.nome, dados.descricao, dados.empresa_id, usuario_id
    )
    return {"id": projeto.id, "nome": projeto.nome, "cor": getattr(projeto, "cor", "teal")}


@router.get("/{projeto_id:int}")
def detalhe_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    projeto = repo.buscar_por_id(projeto_id)
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return {
        "id": projeto.id, "nome": projeto.nome, "descricao": projeto.descricao,
        "empresa_id": projeto.empresa_id, "status": projeto.status,
        "cor": getattr(projeto, "cor", "teal")
    }


@router.put("/{projeto_id:int}")
def editar_projeto(projeto_id: int, dados: ProjetoEditInput, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        projeto = EditarProjetoUseCase(repo, membro_repo).executar(
            projeto_id, dados.nome, dados.descricao, usuario_id
        )
        return {"id": projeto.id, "nome": projeto.nome, "cor": getattr(projeto, "cor", "teal")}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{projeto_id:int}/arquivar")
def arquivar_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        projeto = ArquivarProjetoUseCase(repo, membro_repo).executar(projeto_id, usuario_id)
        return {"id": projeto.id, "status": projeto.status, "cor": getattr(projeto, "cor", "teal")}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{projeto_id:int}", status_code=204)
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


@router.delete("/{projeto_id:int}/sair", status_code=204)
def sair_do_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    projeto_repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        SairProjetoUseCase(membro_repo, projeto_repo).executar(projeto_id, usuario_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/empresa/{empresa_id:int}/ocultar", status_code=204)
def ocultar_projetos_da_empresa(empresa_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    projeto_repo = ProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        OcultarProjetosPorEmpresaUseCase(projeto_repo, membro_repo).executar(empresa_id, usuario_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{projeto_id}/papeis", response_model=list[PapelProjetoOut])
def listar_papeis_projeto(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    """
    Retorna os papéis (roles) disponíveis no projeto.
    Este MS não possui tabela de papéis; então os papéis são derivados dos roles existentes em membros_projeto,
    com um mapeamento padrão de descrições/permissões.
    """
    repo = ProjetoRepositoryImpl(db)
    projeto = repo.buscar_por_id(projeto_id)
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    membro_repo = MembroProjetoRepositoryImpl(db)
    # exige que o usuário seja membro para visualizar
    if not membro_repo.buscar(projeto_id, usuario_id):
        raise HTTPException(status_code=403, detail="Sem acesso ao projeto")

    roles = {(m.role or "").strip().lower() for m in membro_repo.listar_por_projeto(projeto_id)}
    roles.discard("")

    defaults: dict[str, PapelProjetoOut] = {
        "owner": PapelProjetoOut(
            nome="Owner",
            descricao="Controle total do projeto",
            permissoes="gerenciar_membros,editar_configuracoes,excluir_projeto",
        ),
        "admin": PapelProjetoOut(
            nome="Admin",
            descricao="Pode gerenciar projetos e membros",
            permissoes="gerenciar_membros,editar_configuracoes",
        ),
        "member": PapelProjetoOut(
            nome="Member",
            descricao="Acesso básico à empresa",
            permissoes="ver_projeto",
        ),
    }

    # Sempre retorna o conjunto básico (mesmo que hoje só exista Owner no banco),
    # e adiciona quaisquer roles extras encontrados.
    result: list[PapelProjetoOut] = [defaults["owner"], defaults["admin"], defaults["member"]]

    known = set(defaults.keys())
    extras = [r for r in sorted(roles) if r and r not in known]
    for r in extras:
        result.append(PapelProjetoOut(nome=r.title(), descricao="", permissoes=""))

    return result


@router.get("/{projeto_id}/solicitacoes")
def listar_solicitacoes(projeto_id: int, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    sol_repo = SolicitacaoProjetoRepositoryImpl(db)
    solicitacoes = sol_repo.listar_por_projeto(projeto_id)
    return [{"id": s.id, "usuario_id": s.usuario_id, "status": s.status, "mensagem": getattr(s, "mensagem", None)} for s in solicitacoes]


@router.post("/{projeto_id}/solicitacoes", status_code=201)
def solicitar_acesso(projeto_id: int, dados: SolicitarAcessoInput | None = None, usuario_id: int = Depends(get_usuario_id), db: Session = Depends(get_db)):
    sol_repo = SolicitacaoProjetoRepositoryImpl(db)
    membro_repo = MembroProjetoRepositoryImpl(db)
    try:
        mensagem = dados.mensagem if dados else None
        sol = SolicitarAcessoProjetoUseCase(sol_repo, membro_repo).executar(projeto_id, usuario_id, mensagem=mensagem)
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
