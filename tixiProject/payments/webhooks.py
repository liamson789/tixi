import json, hmac, hashlib, logging, sys
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Purchase, WebhookLog
# Lazy import de raffles.services para evitar circular import

logger = logging.getLogger(__name__)


def verify_wompi_signature(payload_bytes, signature_header, integrity_key):
    """
    Verifica la firma HMAC-SHA256 que Wompi envía en el header X-Wompi-Signature
    
    Wompi calcula:
    signature = HMAC-SHA256(payload, WOMPI_INTEGRITY_KEY)
    
    Args:
        payload_bytes: El body del request raw (bytes)
        signature_header: Valor del header X-Wompi-Signature
        integrity_key: WOMPI_INTEGRITY_KEY de settings
    
    Returns:
        bool: True si la firma es válida
    """
    if not integrity_key:
        logger.warning(" WOMPI_INTEGRITY_KEY no está configurada. Saltando validación HMAC.")
        return True  # En desarrollo sin key, permitir
    
    if not signature_header:
        if settings.DEBUG or 'test' in sys.argv:
            logger.warning("X-Wompi-Signature faltante en DEBUG/test. Se permite para pruebas locales.")
            return True
        logger.error(" Header X-Wompi-Signature faltante")
        return False
    
    # Calcular firma esperada
    calculated_signature = hmac.new(
        integrity_key.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Comparar de forma segura para evitar timing attacks
    is_valid = hmac.compare_digest(calculated_signature, signature_header)
    
    if not is_valid:
        logger.error(
            f"❌ Firma inválida\n"
            f"   Esperada: {calculated_signature}\n"
            f"   Recibida: {signature_header}"
        )
    
    return is_valid


@csrf_exempt
@require_http_methods(["POST"])
def wompi_webhook(request):
    """
    Webhook para recibir notificaciones de pago de Wompi
    
    Documentación de Wompi:
    https://developers.wompi.sv/webhook
    
    Headers esperados:
    - X-Wompi-Signature: HMAC-SHA256(body, WOMPI_INTEGRITY_KEY)
    
    Payload esperado:
    {
        "ResultadoTransaccion": "ExitosaAprobada" | "Rechazada" | "Pendiente",
        "EnlacePago": {
            "IdentificadorEnlaceComercio": "ref-12345",
            "Monto": 10.50,
            "Descripcion": "Compra de números de rifa"
        },
        "Transaccion": {
            "IdTransaccion": "TXN-12345",
            "FechaTransaccion": "2026-02-12"
        }
    }
    """
    
    payload_bytes = request.body
    webhook_log = WebhookLog(payload={})  # Inicializar para registrar errores
    
    try:
        # 1️⃣ Validar Content-Type
        content_type = (request.content_type or '').lower()
        if not content_type.startswith('application/json'):
            webhook_log.status = 'invalid_json'
            webhook_log.error_message = f"Content-Type inválido: {request.content_type}"
            webhook_log.save()
            logger.warning(f"❌ Content-Type inválido: {request.content_type}")
            return JsonResponse({'error': 'Invalid Content-Type'}, status=400)
        
        # 2️⃣ Validar firma HMAC (CRÍTICO en producción)
        signature = request.headers.get('X-Wompi-Signature')
        integrity_key = getattr(settings, 'WOMPI_INTEGRITY_KEY', None)
        
        if not verify_wompi_signature(payload_bytes, signature, integrity_key):
            webhook_log.status = 'invalid_signature'
            webhook_log.signature_valid = False
            webhook_log.error_message = "Firma HMAC inválida"
            webhook_log.save()
            logger.error("❌ Firma HMAC inválida - Rechazando webhook")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        webhook_log.signature_valid = True
        
        # 3️⃣ Parsear JSON
        try:
            payload = json.loads(payload_bytes)
            webhook_log.payload = payload
        except json.JSONDecodeError as e:
            webhook_log.status = 'invalid_json'
            webhook_log.error_message = f"JSON inválido: {str(e)}"
            webhook_log.save()
            logger.error(f"❌ JSON inválido: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # 4️⃣ Extraer datos del payload
        resultado = payload.get("ResultadoTransaccion")
        enlace = payload.get("EnlacePago", {})
        reference = enlace.get("IdentificadorEnlaceComercio")
        transaccion = payload.get("Transaccion", {})
        
        webhook_log.reference = reference
        webhook_log.resultado_transaccion = resultado
        
        logger.info(
            f"📥 Webhook recibido:\n"
            f"   Reference: {reference}\n"
            f"   Resultado: {resultado}\n"
            f"   Monto: ${enlace.get('Monto', 'N/A')}\n"
            f"   TX ID: {transaccion.get('IdTransaccion', 'N/A')}"
        )
        
        # 5️⃣ Validar que existe el reference
        if not reference:
            webhook_log.status = 'missing_reference'
            webhook_log.error_message = "Reference (IdentificadorEnlaceComercio) faltante"
            webhook_log.save()
            logger.warning("❌ Reference faltante en payload")
            return JsonResponse({'error': 'Missing reference'}, status=400)
        
        # 6️⃣ Obtener Purchase
        try:
            purchase = Purchase.objects.get(reference=reference)
        except Purchase.DoesNotExist:
            webhook_log.status = 'purchase_not_found'
            webhook_log.error_message = f"Purchase no encontrada: {reference}"
            webhook_log.save()
            logger.error(f"❌ Purchase no encontrada: {reference}")
            return JsonResponse({'error': 'Purchase not found'}, status=404)
        
        # 7️⃣ Procesar según resultado
        # Lazy import para evitar circular import
        from raffles.services import finalize_raffle_numbers, release_reserved_numbers
        
        if resultado == "ExitosaAprobada":
            if purchase.status == "paid":
                webhook_log.status = 'processed'
                webhook_log.processed_at = timezone.now()
                webhook_log.save()
                logger.info(f"ℹ️ Webhook duplicado ignorado (ya paid): {reference}")
                return JsonResponse({'status': 'ok'}, status=200)

            logger.info(f"✅ Pago APROBADO: {reference}")
            purchase.status = "paid"
            purchase.save(update_fields=['status'])
            
            try:
                finalize_raffle_numbers(purchase)
                logger.info(f"✅ Números finalizados para {reference}")
            except Exception as e:
                logger.error(f"❌ Error finalizando números: {e}")
                webhook_log.status = 'error'
                webhook_log.error_message = f"Error finalizando números: {str(e)}"
                webhook_log.save()
                return JsonResponse({'error': 'Failed to finalize numbers'}, status=500)
            
            webhook_log.status = 'processed'
        
        else:
            if purchase.status == "paid":
                webhook_log.status = 'processed'
                webhook_log.processed_at = timezone.now()
                webhook_log.error_message = f"Se ignoró downgrade de paid a {resultado}"
                webhook_log.save()
                logger.warning(f"⚠️ Webhook ignorado para compra ya pagada: {reference} ({resultado})")
                return JsonResponse({'status': 'ok'}, status=200)

            if purchase.status == "failed":
                webhook_log.status = 'processed'
                webhook_log.processed_at = timezone.now()
                webhook_log.save()
                logger.info(f"ℹ️ Webhook duplicado ignorado (ya failed): {reference}")
                return JsonResponse({'status': 'ok'}, status=200)

            logger.warning(f"❌ Pago RECHAZADO/PENDIENTE: {reference} - {resultado}")
            purchase.status = "failed"
            purchase.save(update_fields=['status'])
            
            try:
                release_reserved_numbers(purchase)
                logger.info(f"✅ Números liberados para {reference}")
            except Exception as e:
                logger.error(f"❌ Error liberando números: {e}")
                webhook_log.status = 'error'
                webhook_log.error_message = f"Error liberando números: {str(e)}"
                webhook_log.save()
                return JsonResponse({'error': 'Failed to release numbers'}, status=500)
            
            webhook_log.status = 'processed'
        
        # 8️⃣ Registrar éxito
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        logger.info(f"✅ Webhook procesado exitosamente: {reference}")
        
        return JsonResponse({'status': 'ok'}, status=200)
    
    except Exception as e:
        webhook_log.status = 'error'
        webhook_log.error_message = f"Error inesperado: {str(e)}"
        webhook_log.save()
        logger.exception(f"❌ Error inesperado en webhook: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
