from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.exceptions import RequestValidationError

from http import HTTPStatus

from routers import pacientes, atendimento, prescricao

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou especifique seus domínios ["http://localhost:3000", etc.]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Captura erros de validação do Pydantic e retorna APENAS o XML 
    armazenado na mensagem de erro.
    """
    # Pegamos apenas a mensagem (msg) do primeiro erro encontrado
    # que contém o nosso XML montado no field_validator
    erros = exc.errors()
    
    # Se houver erros, pegamos a mensagem do primeiro
    if erros:
        # O Pydantic V2 coloca "Value error, " antes da mensagem personalizada.
        # Vamos limpar isso para ficar só o XML puro.
        xml_puro = erros[0]['msg'].replace("Value error, ", "")
        
        return Response(
            content=xml_puro, 
            media_type="application/xml", 
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY
        )
    
    # Fallback caso não haja mensagem (improvável)
    return Response(content="<error>Erro de validação desconhecido</error>", media_type="application/xml", status_code=422)

app.include_router(pacientes.router)
app.include_router(atendimento.router)
app.include_router(prescricao.router)