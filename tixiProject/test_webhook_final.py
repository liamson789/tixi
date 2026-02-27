#!/usr/bin/env python
"""Script manual completo para probar webhook con setup básico."""
import os
import json
import hmac
import hashlib
from datetime import datetime, timedelta


def main():
    import django
    import requests

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
    django.setup()

    from django.conf import settings
    from django.contrib.auth.models import User
    from raffles.models import Raffle
    from payments.models import Purchase

    webhook_url = "http://localhost:8000/webhook/wompi/"
    integrity_key = settings.WOMPI_INTEGRITY_KEY

    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@test.com', 'is_staff': True},
    )

    raffle, _ = Raffle.objects.get_or_create(
        title='Test Raffle',
        defaults={
            'description': 'Rifa de prueba para webhooks',
            'price_per_number': 1.00,
            'draw_date': datetime.now() + timedelta(days=1),
            'min_sales_percentage': 50,
        },
    )

    purchase, _ = Purchase.objects.get_or_create(
        reference="WEBHOOK-TEST-001",
        defaults={
            'user': user,
            'raffle': raffle,
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
        print(response.text)
    except requests.exceptions.RequestException as error:
        print(f"Error de conexión/solicitud: {error}")


if __name__ == '__main__':
    main()
