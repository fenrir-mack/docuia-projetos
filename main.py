from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.projeto_router import router as projeto_router
from infrastructure.database.conexao import engine
from infrastructure.database.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DocuIA — MS3 Projetos",
    description="Microserviço responsável por projetos, membros e solicitações",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://docuia-frontend-hdc8hzfqbqebc6cp.brazilsouth-01.azurewebsites.net",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from sqlalchemy import text

app.include_router(projeto_router)


def _ensure_schema():
    # Migração leve (sem Alembic): garante coluna `mensagem` nas solicitações.
    try:
        with engine.connect() as connection:
            has_col = connection.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'solicitacoes_projeto' AND column_name = 'mensagem'"
                )
            ).first()
            if not has_col:
                connection.execute(text("ALTER TABLE solicitacoes_projeto ADD COLUMN mensagem TEXT"))
                connection.commit()
    except Exception:
        pass


_ensure_schema()


@app.get("/")
def health_check():
    return {"status": "ok", "servico": "ms3_projetos"}

@app.get("/health")
def database_health():
    """Verifica se o banco de dados está acessível."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "servico": "ms3_projetos"}
    except Exception as e:
        return {
            "status": "error", 
            "database": "disconnected", 
            "details": str(e),
            "servico": "ms3_projetos"
        }
