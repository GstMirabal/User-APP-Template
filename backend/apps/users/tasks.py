import logging

# Intentamos importar la app de Celery si está configurada en config/celery_app.py
# Si no existe aún, las tareas se definirán como funciones de espera (task placeholders).
try:
    from config.celery_app import app
except ImportError:
    # Fallback para desarrollo sin Celery configurado aún
    def task(func):
        return func

    app = type("CeleryStub", (), {"task": task})

logger = logging.getLogger(__name__)


@app.task
def send_verification_email_task(user_id: str, otp: str) -> None:
    """
    Tarea asíncrona para el envío de códigos de verificación.

    Se ejecutará en el worker de Celery para no bloquear el hilo de respuesta de la API.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        # Lógica de integración con el proveedor de Email (SendGrid, Mailgun, etc.)
        # Por ahora mantenemos el log de auditoría.
        logger.info(f"[CELERY] Sending OTP {otp} to user {user.email}")

    except User.DoesNotExist:
        logger.error(
            f"[CELERY] Attempted to send verification to non-existent user {user_id}"
        )


@app.task
def send_welcome_email_task(user_id: str) -> None:
    """
    Envía un email de bienvenida formal una vez la cuenta está verificada.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        logger.info(f"[CELERY] Sending Welcome Email to {user.email}")

    except User.DoesNotExist:
        logger.error(
            f"[CELERY] Attempted to send welcome email to non-existent user {user_id}"
        )


@app.task
def clear_expired_verification_tokens_task() -> None:
    """
    Tarea periódica para limpiar tokens de verificación huérfanos o caducados.
    """
    logger.info("[CELERY] Cleaning up expired verification secrets...")
    # Lógica de limpieza masiva aquí.
