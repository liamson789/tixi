import json, hmac, hashlib
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Purchase
from raffles.services import finalize_raffle_numbers, release_reserved_numbers

@csrf_exempt
def wompi_webhook(request):
    payload = json.loads(request.body)

    resultado = payload.get("ResultadoTransaccion")
    enlace = payload.get("EnlacePago", {})
    reference = enlace.get("IdentificadorEnlaceComercio")

    if not reference:
        return HttpResponse(status=400)

    try:
        purchase = Purchase.objects.get(reference=reference)
    except Purchase.DoesNotExist:
        return HttpResponse(status=404)

    if resultado == "ExitosaAprobada":
        purchase.status = "paid"
        purchase.save()

        #  AQUÍ SE CONSUMA LA RIFA
        finalize_raffle_numbers(purchase)

    else:
        purchase.status = "failed"
        purchase.save()
        release_reserved_numbers(purchase)

    return HttpResponse(status=200)
