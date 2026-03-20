import logging
import httpx

from fastapi import Request, HTTPException, status
from fastapi.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


async def reenviar_peticion(request: Request, url_destino: str) -> Response:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() != "host"
    }

    body = await request.body()
    params = str(request.url.query) if request.url.query else None

    try:
        async with httpx.AsyncClient(timeout=settings.TIMEOUT_SERVICIOS, follow_redirects=False) as client:
            respuesta = await client.request(
                method=request.method,
                url=url_destino,
                headers=headers,
                content=body,
                params=params,
            )
        return Response(
            content=respuesta.content,
            status_code=respuesta.status_code,
            headers=dict(respuesta.headers),
            media_type=respuesta.headers.get("content-type"),
        )

    except httpx.ConnectError:
        logger.error(f"No se pudo conectar a: {url_destino}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microservicio no disponible. Intente más tarde.",
        )
    except httpx.TimeoutException:
        logger.error(f"Timeout al conectar con: {url_destino}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="El microservicio tardó demasiado en responder.",
        )
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al comunicarse con el microservicio.",
        )