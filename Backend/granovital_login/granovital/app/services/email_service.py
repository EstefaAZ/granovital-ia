# =============================================================
# app/services/email_service.py
# Servicio de envío de correos electrónicos
# =============================================================

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import random
import string

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio para envío de correos electrónicos usando SMTP.
    """

    @staticmethod
    def _generar_codigo_verificacion(length: int = settings.EMAIL_VERIFICATION_CODE_LENGTH) -> str:
        """Genera un código de verificación aleatorio con letras y números."""
        # Generar códigos variados: letras, números o mixtos
        tipo = random.choice(['letras', 'numeros', 'mixto'])
        
        if tipo == 'letras':
            # Solo letras mayúsculas (sin ambigüedades como O/0, l/1)
            caracteres = 'ABCDEFGHJKMNPQRSTUVWXYZ'
        elif tipo == 'numeros':
            # Solo números
            caracteres = '0123456789'
        else:  # mixto
            # Letras y números (sin ambigüedades)
            caracteres = 'ABCDEFGHJKMNPQRSTUVWXYZ0123456789'
        
        return ''.join(random.choices(caracteres, k=length))

    @staticmethod
    def enviar_codigo_verificacion(correo: str) -> str:
        """
        Envía un código de verificación al correo especificado.

        Args:
            correo: Dirección de email del destinatario

        Returns:
            Código de verificación generado

        Raises:
            Exception: Si hay error enviando el email
        """
        if not settings.EMAIL_ENABLED:
            logger.warning("Email service disabled. Using dummy code for development.")
            return "123456"  # Código dummy para desarrollo

        codigo = EmailService._generar_codigo_verificacion()

        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg['To'] = correo
            msg['Subject'] = "Código de verificación - GranoVital IA"

            # Cuerpo del mensaje
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #2D6A4F; color: white; padding: 20px; text-align: center;">
                    <h1>GranoVital IA</h1>
                    <p>Sistema de Gestión Caficultora</p>
                </div>

                <div style="padding: 30px; background-color: #f9f9f9;">
                    <h2 style="color: #2D6A4F;">Código de Verificación</h2>

                    <p>Hola,</p>

                    <p>Has solicitado registrarte en GranoVital IA. Tu código de verificación es:</p>

                    <div style="background-color: white; border: 2px solid #2D6A4F; border-radius: 8px;
                                padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #2D6A4F; font-size: 32px; margin: 0; letter-spacing: 5px;">
                            {codigo}
                        </h1>
                    </div>

                    <p><strong>Este código expira en {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} minutos.</strong></p>

                    <p>Si no solicitaste este código, puedes ignorar este mensaje.</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                    <p style="color: #666; font-size: 12px;">
                        Universidad Católica Luis Amigó<br>
                        GranoVital IA v{settings.APP_VERSION}
                    </p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
            Código de verificación - GranoVital IA

            Tu código de verificación es: {codigo}

            Este código expira en {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} minutos.

            Si no solicitaste este código, puedes ignorar este mensaje.

            Universidad Católica Luis Amigó - GranoVital IA v{settings.APP_VERSION}
            """

            # Adjuntar versiones HTML y texto plano
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Enviar email
            server = smtplib.SMTP(settings.EMAIL_SMTP_SERVER, settings.EMAIL_SMTP_PORT)
            server.starttls()
            server.login(settings.EMAIL_SMTP_USERNAME, settings.EMAIL_SMTP_PASSWORD.get_secret_value())
            server.sendmail(settings.EMAIL_FROM, correo, msg.as_string())
            server.quit()

            logger.info(f"Código de verificación enviado exitosamente a: {correo}")
            return codigo

        except Exception as e:
            logger.error(f"Error enviando código de verificación a {correo}: {str(e)}")
            raise Exception(f"No se pudo enviar el código de verificación: {str(e)}")

    @staticmethod
    def enviar_bienvenida(correo: str, nombre: str) -> None:
        """
        Envía email de bienvenida al usuario registrado.

        Args:
            correo: Email del usuario
            nombre: Nombre del usuario
        """
        if not settings.EMAIL_ENABLED:
            logger.info(f"Email service disabled. Skipping welcome email to {correo}")
            return

        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg['To'] = correo
            msg['Subject'] = "¡Bienvenido a GranoVital IA!"

            # Cuerpo del mensaje
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #2D6A4F; color: white; padding: 20px; text-align: center;">
                    <h1>GranoVital IA</h1>
                    <p>Sistema de Gestión Caficultora</p>
                </div>

                <div style="padding: 30px; background-color: #f9f9f9;">
                    <h2 style="color: #2D6A4F;">¡Bienvenido, {nombre}!</h2>

                    <p>Tu cuenta en GranoVital IA ha sido creada exitosamente.</p>

                    <p>Ya puedes acceder a todas las funcionalidades del sistema:</p>

                    <ul style="color: #555;">
                        <li>Gestión de cultivos y lotes</li>
                        <li>Monitoreo ambiental</li>
                        <li>Análisis de mercado</li>
                        <li>Reportes y trazabilidad</li>
                        <li>Inteligencia artificial para predicción de enfermedades</li>
                    </ul>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/login"
                           style="background-color: #2D6A4F; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Acceder al Sistema
                        </a>
                    </div>

                    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                    <p style="color: #666; font-size: 12px;">
                        Universidad Católica Luis Amigó<br>
                        GranoVital IA v{settings.APP_VERSION}
                    </p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
            ¡Bienvenido a GranoVital IA, {nombre}!

            Tu cuenta ha sido creada exitosamente. Ya puedes acceder a todas las funcionalidades del sistema.

            Accede aquí: http://localhost:3000/login

            Universidad Católica Luis Amigó - GranoVital IA v{settings.APP_VERSION}
            """

            # Adjuntar versiones HTML y texto plano
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Enviar email
            server = smtplib.SMTP(settings.EMAIL_SMTP_SERVER, settings.EMAIL_SMTP_PORT)
            server.starttls()
            server.login(settings.EMAIL_SMTP_USERNAME, settings.EMAIL_SMTP_PASSWORD.get_secret_value())
            server.sendmail(settings.EMAIL_FROM, correo, msg.as_string())
            server.quit()

            logger.info(f"Email de bienvenida enviado exitosamente a: {correo}")

        except Exception as e:
            logger.error(f"Error enviando email de bienvenida a {correo}: {str(e)}")
            # No lanzamos excepción para no fallar el registro