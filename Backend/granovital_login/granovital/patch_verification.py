from pathlib import Path
import sys

path = Path('app/services/verification_service.py')
text = path.read_text(encoding='utf-8')
old = """        key = self._get_key(email)

        try:
            assert self.redis_client is not None
            self.redis_client.delete(key)
            logger.info(f\"Código de verificación eliminado para: {email}\")
        except Exception as e:
            logger.error(f\"Error eliminando código de verificación para {email}: {str(e)}\")
"""
new = """        key = self._get_key(email)

        try:
            assert self.redis_client is not None
            self.redis_client.delete(key)
            logger.info(f\"Código de verificación eliminado para: {email}\")
        except AssertionError:
            logger.warning(\"Redis client no está disponible al eliminar el código\")
        except Exception as e:
            logger.error(f\"Error eliminando código de verificación para {email}: {str(e)}\")
"""

if old not in text:
    print('old block not found')
    sys.exit(1)

path.write_text(text.replace(old, new), encoding='utf-8')
print('patched')
