# 📋 Documentación: Webhooks de Wompi - Estructura y Validación

## 🔐 Validación HMAC-SHA256 (Implementada)

### Cómo funciona
1. **Wompi calcula** una firma HMAC usando tu `WOMPI_INTEGRITY_KEY`:
   ```
   signature = HMAC-SHA256(body_raw, WOMPI_INTEGRITY_KEY)
   ```

2. **Wompi envía** el webhook con el header:
   ```
   X-Wompi-Signature: abc123def456... (hex string)
   ```

3. **Tu servidor valida** recalculando la firma y comparándola:
   ```python
   calculated = HMAC-SHA256(request.body, WOMPI_INTEGRITY_KEY)
   if calculated == X-Wompi-Signature:
       # Válido, es realmente de Wompi
   else:
       # Inválido, rechazar
   ```

### Ventajas de HMAC-SHA256
- ✅ Verifica que el webhook **viene de Wompi**
- ✅ Verifica que el body **no fue modificado** en tránsito
- ✅ Imposible falsificar sin conocer `WOMPI_INTEGRITY_KEY`
- ✅ Protege contra ataques man-in-the-middle

---

## 📦 Estructura del Payload de Wompi

### Request HTTP
```
POST /webhook/wompi/ HTTP/1.1
Host: tu-dominio.com
Content-Type: application/json
X-Wompi-Signature: 7c8f9a1e2d3c4b5a6f7e8d9c0b1a2f3e
Content-Length: 342

{
  "ResultadoTransaccion": "ExitosaAprobada",
  "EnlacePago": {
    "IdentificadorEnlaceComercio": "ORDER-12345",
    "Monto": 10.50,
    "Descripcion": "Compra de números de rifa"
  },
  "Transaccion": {
    "IdTransaccion": "TXN-9876543210",
    "FechaTransaccion": "2026-02-12T15:30:45Z"
  }
}
```

### Estructura Detallada

#### `ResultadoTransaccion` (REQUERIDO)
Posibles valores:
- `"ExitosaAprobada"` — ✅ Pago APROBADO: finalizar números
- `"Rechazada"` — ❌ Pago RECHAZADO: liberar números
- `"Pendiente"` — ⏳ Aún en proceso: esperar a otro webhook

**Lógica de negocio:**
```python
if resultado == "ExitosaAprobada":
    # Marcar números como VENDIDOS (is_sold=True)
    finalize_raffle_numbers(purchase)
else:
    # Liberar números reservados (is_reserved=False)
    release_reserved_numbers(purchase)
```

#### `EnlacePago` (REQUERIDO)
```json
{
  "IdentificadorEnlaceComercio": "ORDER-12345",  // Tu reference único
  "Monto": 10.50,                                // Monto pagado
  "Descripcion": "Compra de números"             // Descripción del pago
}
```

**`IdentificadorEnlaceComercio`** es **CRÍTICO**:
- Es el `reference` que creaste en `Purchase`
- Lo usamos para encontrar qué Purchase se pagó
- Si no existe en BD → Rechazar webhook (404)

#### `Transaccion` (OPCIONAL pero RECOMENDADO)
```json
{
  "IdTransaccion": "TXN-9876543210",  // ID único del pago en Wompi
  "FechaTransaccion": "2026-02-12"    // Fecha del pago
}
```

Úsalo para auditoría, pero no es crítico para la lógica.

---

## 🔍 Validación Implementada en `payments/webhooks.py`

### 1️⃣ Validación de Firma HMAC
```python
def verify_wompi_signature(payload_bytes, signature_header, integrity_key):
    calculated = hmac.new(
        integrity_key.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated, signature_header)
```

**Estado actual:** ✅ IMPLEMENTADA
- Si `WOMPI_INTEGRITY_KEY` está configurada → Valida firma
- Si no está → Log de warning, pero permite (desarrollo)

### 2️⃣ Validación de Content-Type
```python
if request.content_type != 'application/json':
    return JsonResponse({'error': 'Invalid Content-Type'}, status=400)
```

**Estado:** ✅ IMPLEMENTADA

### 3️⃣ Validación de Método HTTP
```python
@require_http_methods(["POST"])
def wompi_webhook(request):
    pass
```

**Estado:** ✅ IMPLEMENTADA
- Rechaza GET, PUT, DELETE, etc.
- Solo acepta POST

### 4️⃣ Validación de JSON
```python
try:
    payload = json.loads(payload_bytes)
except json.JSONDecodeError:
    return JsonResponse({'error': 'Invalid JSON'}, status=400)
```

**Estado:** ✅ IMPLEMENTADA

### 5️⃣ Validación de Reference
```python
reference = payload.get('EnlacePago', {}).get('IdentificadorEnlaceComercio')
if not reference:
    return JsonResponse({'error': 'Missing reference'}, status=400)
```

**Estado:** ✅ IMPLEMENTADA

### 6️⃣ Búsqueda de Purchase
```python
try:
    purchase = Purchase.objects.get(reference=reference)
except Purchase.DoesNotExist:
    return JsonResponse({'error': 'Purchase not found'}, status=404)
```

**Estado:** ✅ IMPLEMENTADA

---

## 📊 Modelo `WebhookLog` para Auditoría

Creamos este modelo para registrar **todos** los webhooks (exitosos o fallidos):

```python
class WebhookLog(models.Model):
    payload = models.JSONField()  # Payload completo
    status = models.CharField(max_length=30, choices=[
        ('received', 'Recibido'),
        ('valid', 'Válido'),
        ('invalid_signature', 'Firma inválida'),
        ('invalid_json', 'JSON inválido'),
        ('missing_reference', 'Reference faltante'),
        ('purchase_not_found', 'Purchase no encontrada'),
        ('processed', 'Procesado'),
        ('error', 'Error'),
    ])
    reference = models.CharField(max_length=100)
    resultado_transaccion = models.CharField(max_length=50)
    signature_valid = models.BooleanField()
    error_message = models.TextField(null=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)
```

**Beneficios:**
- ✅ Ver todos los webhooks recibidos
- ✅ Debuggear problemas (ver error_message)
- ✅ Auditoría de pagos
- ✅ Detectar intentos de falsificación

---

## 🧪 Pruebas Manuales

### Test 1: Webhook exitoso
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: application/json" \
  -H "X-Wompi-Signature: tu-firma-aqui" \
  -d '{
    "ResultadoTransaccion": "ExitosaAprobada",
    "EnlacePago": {
      "IdentificadorEnlaceComercio": "ORDER-TEST-001",
      "Monto": 10.00
    }
  }'
```

**Respuesta esperada:** `{"status": "ok"}` (200)

### Test 2: Reference inválido
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: application/json" \
  -d '{
    "ResultadoTransaccion": "ExitosaAprobada",
    "EnlacePago": {}
  }'
```

**Respuesta esperada:** `{"error": "Missing reference"}` (400)

### Test 3: Purchase no encontrada
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: application/json" \
  -d '{
    "ResultadoTransaccion": "ExitosaAprobada",
    "EnlacePago": {
      "IdentificadorEnlaceComercio": "INVALID-REF"
    }
  }'
```

**Respuesta esperada:** `{"error": "Purchase not found"}` (404)

### Test 4: JSON inválido
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```

**Respuesta esperada:** `{"error": "Invalid JSON"}` (400)

### Test 5: Content-Type incorrecto
```bash
curl -X POST http://localhost:8000/webhook/wompi/ \
  -H "Content-Type: text/plain" \
  -d '{"test": "data"}'
```

**Respuesta esperada:** `{"error": "Invalid Content-Type"}` (400)

---

## ⚙️ Configuración en `settings.py`

```python
# Credenciales de Wompi (descomenta y rellena)
WOMPI_API_SECRET = None  # Activar cuando tengas credenciales
WOMPI_INTEGRITY_KEY = None  # CRÍTICO para validar firma HMAC
WOMPI_PUBLIC_KEY = None
WOMPI_PRIVATE_KEY = None
NGROK_URL = None  # Para development tunneling
```

**Todo configurado en:**
- ✅ `tixiProject/settings.py` (lineas ~150)

---

## 📝 Logging

El webhook genera logs detallados en **consola** (se pueden redirigir a archivo):

```
[INFO] 2026-02-12 15:30:45 - payments.webhooks - 📥 Webhook recibido:
   Reference: ORDER-12345
   Resultado: ExitosaAprobada
   Monto: $10.50
   TX ID: TXN-9876543210

[INFO] 2026-02-12 15:30:46 - payments.webhooks - ✅ Pago APROBADO: ORDER-12345
[INFO] 2026-02-12 15:30:46 - payments.webhooks - ✅ Números finalizados para ORDER-12345
[INFO] 2026-02-12 15:30:46 - payments.webhooks - ✅ Webhook procesado exitosamente: ORDER-12345
```

---

## 🚀 Próximos Pasos

### Antes de ir a Producción:
1. ✅ Obtener `WOMPI_API_SECRET`, `WOMPI_INTEGRITY_KEY`, `WOMPI_PUBLIC_KEY` de Wompi
2. ✅ Configurarlos en **environment variables** (NO hardcodear en settings.py)
3. ✅ Configurar URL pública de ngrok o servidor para que Wompi pueda alcanzar el webhook
4. ✅ Registrar URL de webhook en panel de Wompi: `https://tu-dominio.com/webhook/wompi/`
5. ✅ Correr migration: `python manage.py migrate payments`
6. ✅ Testear con Wompi en sandbox first
7. ✅ Revisar logs de `WebhookLog` en admin

### En Producción:
1. Usar `from decouple import config` para leer variables de ambiente
2. Agregar logs persistentes a archivo
3. Configurar alertas si webhook falla
4. Revisar auditoría de `WebhookLog` regularmente
5. Implementar retry logic si `finalize_raffle_numbers()` falla

---

## 📞 Preguntas Frecuentes

**P: ¿Qué pasa si Wompi envía un webhook pero nuestro servidor está offline?**
R: Wompi lo reintentará según su política (típicamente 3-5 veces). Registramos en `WebhookLog` incluso si falla.

**P: ¿Qué pasa si la firma HMAC es inválida?**
R: Rechazamos con 401 Unauthorized. En `WebhookLog` queda registrado como `invalid_signature`.

**P: ¿Puedo testear sin `WOMPI_INTEGRITY_KEY`?**
R: Sí, en desarrollo si no está configurada solo log warning y permite. En producción debes tenerla.

**P: ¿Dónde veo los logs de webhook?**
R: 
- Consola durante desarrollo
- Admin de Django → WebhookLog (tabla con historial)
- Archivo si lo configuramos (TODO)

---

## 📚 Referencias

- [Documentación Wompi Webhooks](https://developers.wompi.sv/webhook)
- [HMAC en Python](https://docs.python.org/3/library/hmac.html)
- [Django logging](https://docs.djangoproject.com/en/stable/topics/logging/)
