#!/usr/bin/env python
"""Script manual para probar webhook de Wompi."""
import os
import json


def main():
    import django
    import requests

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
    django.setup()

    from payments.models import Purchase

    webhook_url = "http://localhost:8000/webhook/wompi/"

    purchase, _ = Purchase.objects.get_or_create(
        reference="TEST-WEBHOOK-001",
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
            "Descripcion": "Test payment",
        },
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        print(f"HTTP {response.status_code}")
    except requests.exceptions.RequestException as error:
        print(f"Error de conexión/solicitud: {error}")


if __name__ == '__main__':
    main()
