"""
Webhooks mejorados para pagos con Wompi
Incluye validación de firma, logging, y mejor manejo de errores
"""
import json
import hmac
import hashlib
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Purchase
from raffles.services import finalize_raffle_numbers, release_reserved_numbers

# Configurar logger
logger = logging.getLogger(__name__)


def verify_wompi_signature(payload_bytes, signature, integrity_key):
    """
    Verifica que el webhook viene realmente de Wompi usando HMAC
    Wompi envía una firma en el header X-Wompi-Signature
    
    Args:
        payload_bytes: El body del request raw
        signature: Firma desde header X-Wompi-Signature
        integrity_key: WOMPI_INTEGRITY_KEY de settings
    
    Returns:
        bool: True si la firma es válida
    """
    if not integrity_key:
        logger.warning("WOMPI_INTEGRITY_KEY no está configurada en settings")
        return False
    
    # Wompi usa HMAC-SHA256
    calculated_signature = hmac.new(
        integrity_key.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Comparar de forma segura para evitar timing attacks
    return hmac.compare_digest(calculated_signature, signature)


@csrf_exempt
@require_http_methods(["POST"])
def wompi_webhook(request):
    """
    Webhook para recibir notificaciones de pago de Wompi
    
    Valida:
    - Método HTTP (POST)
    - Firma HMAC (seguridad)
    - Estructura del payload
    - Existencia de Purchase
    
    Actualiza:
    - Estado de Purchase (paid/failed)
    - Números rifados (finalizados o liberados)
    """
    
    try:
        # 1. Validar Content-Type
        if request.content_type != 'application/json':
            logger.warning(f"Webhook recibió Content-Type inválido: {request.content_type}")
            return JsonResponse(
                {'error': 'Invalid Content-Type'}, 
                status=400
            )
        
        # 2. Obtener payload raw para validar firma
        payload_bytes = request.body
        
        # 3. Validar firma HMAC (recomendado en producción)
        integrity_key = getattr(settings, 'WOMPI_INTEGRITY_KEY', None)
        if integrity_key:
            signature = request.headers.get('X-Wompi-Signature')
            if not signature:
                logger.warning("Webhook sin firma X-Wompi-Signature")
                return JsonResponse(
                    {'error': 'Missing signature'}, 
                    status=401
                )
            
            if not verify_wompi_signature(payload_bytes, signature, integrity_key):
                logger.error("Firma HMAC inválida en webhook")
                return JsonResponse(
                    {'error': 'Invalid signature'}, 
                    status=401
                )
        
        # 4. Parsear JSON
        try:
            payload = json.loads(payload_bytes)
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido en webhook: {e}")
            return JsonResponse(
                {'error': 'Invalid JSON'}, 
                status=400
            )
        
        # 5. Extraer datos del payload
        resultado = payload.get("ResultadoTransaccion")
        enlace = payload.get("EnlacePago", {})
        reference = enlace.get("IdentificadorEnlaceComercio")
        
        logger.info(f"Webhook recibido - Reference: {reference}, Resultado: {resultado}")
        
        # 6. Validar que el reference existe
        if not reference:
            logger.warning("Webhook sin reference (IdentificadorEnlaceComercio)")
            return JsonResponse(
                {'error': 'Missing reference'}, 
                status=400
            )
        
        # 7. Obtener Purchase
        try:
            purchase = Purchase.objects.get(reference=reference)
        except Purchase.DoesNotExist:
            logger.error(f"Purchase no encontrada: {reference}")
            return JsonResponse(
                {'error': 'Purchase not found'}, 
                status=404
            )
        
        # 8. Procesar según resultado
        if resultado == "ExitosaAprobada":
            logger.info(f"Pago aprobado: {reference}")
            purchase.status = "paid"
            purchase.save()
            
            # Finalizar números (marcar como vendidos)
            try:
                finalize_raffle_numbers(purchase)
                logger.info(f"Números finalizados para {reference}")
            except Exception as e:
                logger.error(f"Error finalizando números: {e}")
                # No retornar error aquí, el pago ya se marcó como pagado
        else:
            logger.warning(f"Pago fallido: {reference} - {resultado}")
            purchase.status = "failed"
            purchase.save()
            
            # Liberar números reservados
            try:
                release_reserved_numbers(purchase)
                logger.info(f"Números liberados para {reference}")
            except Exception as e:
                logger.error(f"Error liberando números: {e}")
        
        # 9. Retornar éxito
        logger.info(f"Webhook procesado exitosamente: {reference}")
        return JsonResponse({'status': 'ok'}, status=200)
    
    except Exception as e:
        logger.exception(f"Error inesperado en webhook: {e}")
        return JsonResponse(
            {'error': 'Internal server error'}, 
            status=500
        )
