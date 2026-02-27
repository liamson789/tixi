# 🔒 Guía de Mejoras para Webhooks de Wompi

## Estado Actual
Tu webhook en `payments/webhooks.py` **funciona** pero le faltan validaciones críticas para producción.

---

## 🚨 Problemas Identificados

### 1. ❌ Sin validación de firma HMAC
**Problema:** Cualquiera podría enviar un webhook falso
```python
# Actual (inseguro)
@csrf_exempt
def wompi_webhook(request):
    payload = json.loads(request.body)  # ¿De verdad es de Wompi?
```

**Solución:** Validar firma HMAC-SHA256 que Wompi envía en header `X-Wompi-Signature`
```python
# Mejorado (seguro)
signature = request.headers.get('X-Wompi-Signature')
if not verify_hmac(request.body, signature, settings.WOMPI_INTEGRITY_KEY):
    return JsonResponse({'error': 'Invalid signature'}, status=401)
```

---

### 2. ❌ Sin manejo de JSON inválido
**Problema:** Si el body no es JSON válido, la app crashea
```python
# Crash si request.body no es JSON válido
payload = json.loads(request.body)
```

**Solución:**
```python
try:
    payload = json.loads(request.body)
except json.JSONDecodeError:
    logger.error("JSON inválido en webhook")
    return JsonResponse({'error': 'Invalid JSON'}, status=400)
```

---

### 3. ❌ Sin validación del método HTTP
**Problema:** El webhook acepta GET, lo que no tiene sentido
```python
# GET /webhook/wompi/ ❌ Debería ser POST únicamente
```

**Solución:**
```python
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def wompi_webhook(request):
    pass
```

---

### 4. ❌ Sin validación de Content-Type
**Problema:** Podría recibir payload no JSON
```python
# application/xml ❌ No manejado
```

**Solución:**
```python
if request.content_type != 'application/json':
    return JsonResponse({'error': 'Invalid Content-Type'}, status=400)
```

---

### 5. ❌ Sin logging
**Problema:** Es imposible debuggear si algo sale mal
```python
# ¿Qué falló? No hay forma de saberlo
```

**Solución:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Webhook recibido - Reference: {reference}")
logger.error(f"Purchase no encontrada: {reference}")
logger.exception(f"Error inesperado: {e}")
```

---

### 6. ❌ Sin enum para ResultadoTransaccion
**Problema:** Strings mágicos, fácil equivocarse
```python
if resultado == "ExitosaAprobada":  # ¿Es "Exitosa Aprobada"? ¿"exitosaaprobada"?
```

**Solución:**
```python
from enum import Enum

class TransactionStatus(Enum):
    APPROVED = "ExitosaAprobada"
    REJECTED = "Rechazada"
    PENDING = "Pendiente"

if resultado == TransactionStatus.APPROVED.value:
    pass
```

---

### 7. ❌ Sin tests unitarios
**Problema:** No hay forma de validar que el webhook funciona
```python
# ¿El webhook funciona? ¿Lo sabemos con seguridad?
```

**Solución:** Ver `payments/tests_webhook.py` (incluído)

---

## 📋 Checklist de Implementación

### Fase 1: Validaciones Básicas (HACER YA)
- [ ] Agregar `@require_http_methods(["POST"])`
- [ ] Validar `Content-Type == 'application/json'`
- [ ] Wrappear `json.loads()` en try/except
- [ ] Agregar logging básico

### Fase 2: Seguridad (PRODUCCIÓN)
- [ ] Implementar validación de firma HMAC-SHA256
- [ ] Usar enums para `ResultadoTransaccion`
- [ ] Agregar tests unitarios
- [ ] Configurar `WOMPI_INTEGRITY_KEY` en settings

### Fase 3: Robustez (OPCIONAL)
- [ ] Agregar retry logic si `finalize_raffle_numbers()` falla
- [ ] Crear modelo `WebhookLog` para auditar
- [ ] Agregar alertas si webhook falla
- [ ] Timeouts para requests externos

---

## 🔧 Cómo Implementar

### Opción A: Usar la versión mejorada que creé
```bash
# Respaldar la original
cp payments/webhooks.py payments/webhooks_original.py

# Usar la mejorada (necesita configurar WOMPI_INTEGRITY_KEY)
cp payments/webhooks_improved.py payments/webhooks.py
```

### Opción B: Mejorar la actual incrementalmente
```python
# payments/webhooks.py
import logging
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])  # ← Agregar esto
def wompi_webhook(request):
    # Validar Content-Type
    if request.content_type != 'application/json':  # ← Agregar
        return JsonResponse({'error': 'Invalid Content-Type'}, status=400)
    
    try:  # ← Agregar
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("JSON inválido")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # ... resto del código ...
    logger.info(f"Webhook: {reference} -> {resultado}")  # ← Agregar logging
```

---

## 🧪 Cómo Testear

### Test unitario
```bash
./env/Scripts/python.exe tixiProject/manage.py test payments.tests_webhook
```

### Test manual  (cuando el servidor esté corriendo)
```bash
python test_webhook.py
```

### Test con curl
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: application/json" \
  -d '{
    "ResultadoTransaccion": "ExitosaAprobada",
    "EnlacePago": {
      "IdentificadorEnlaceComercio": "TEST-001"
    }
  }'
```

---

## 📚 Configuración necesaria en `settings.py`

```python
# settings.py
WOMPI_API_SECRET = "tu-secret-key"  # Ya comentado
WOMPI_INTEGRITY_KEY = "tu-integrity-key"  # AGREGAR ESTO

# Para logging en webhook
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'webhooks.log',
        },
    },
    'loggers': {
        'payments.webhooks': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

---

## ✨ Resumen Rápido

| Prioridad | Tarea | Effort | Impacto |
|-----------|-------|--------|---------|
| 🔴 ALTA | Validar Content-Type + método HTTP | 5 min | Alto |
| 🔴 ALTA | Manejo de JSON inválido | 5 min | Alto |
| 🔴 ALTA | Logging básico | 10 min | Alto |
| 🟡 MEDIA | Validar firma HMAC | 20 min | Crítico |
| 🟡 MEDIA | Tests unitarios | 30 min | Alto |
| 🟢 BAJA | Enums para status | 15 min | Medio |

---

## 📞 ¿Necesitas ayuda?

Te creé estos archivos:
- `payments/webhooks_improved.py` — Versión completa mejorada
- `payments/tests_webhook.py` — Tests unitarios
- `test_webhook.py` — Script para test manual

Puedo implementar cualquiera de estos si lo necesitas.
