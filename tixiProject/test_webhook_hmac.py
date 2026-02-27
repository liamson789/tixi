#!/usr/bin/env python
"""Script manual para probar webhook con firma HMAC."""
import os
import json
import hmac
import hashlib
from datetime import datetime


def main():
    import django
    import requests

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
    django.setup()

    from payments.models import Purchase

    webhook_url = "http://localhost:8000/webhook/wompi/"
    integrity_key = "test-key-secret-123"

    purchase, _ = Purchase.objects.get_or_create(
        reference="WEBHOOK-TEST-001",
        defaults={
            'user_id': 1,
            'raffle_id': 1,
            'amount': 10.00,
            'status': 'pending',
        },
    )

    payload = {
        "ResultadoTransaccion": "ExitosaAprobada",
        "EnlacePago": {
            "IdentificadorEnlaceComercio": purchase.reference,
            "Monto": 10.00,
            "Descripcion": "Test de webhook",
        },
        "Transaccion": {
            "IdTransaccion": "TEST-TX-12345",
            "FechaTransaccion": datetime.now().isoformat(),
        },
    }

    payload_json = json.dumps(payload)
    signature = hmac.new(
        integrity_key.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    try:
        response = requests.post(
            webhook_url,
            data=payload_json,
            headers={
                'Content-Type': 'application/json',
                'X-Wompi-Signature': signature,
            },
            timeout=10,
        )
        print(f"HTTP {response.status_code}")
    except requests.exceptions.RequestException as error:
        print(f"Error de conexión/solicitud: {error}")


if __name__ == '__main__':
    main()
