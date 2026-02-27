import uuid
import requests
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings
from draws.models import Draw

from .models import RaffleList, RaffleNumber, Raffle
from .services import release_reserved_numbers, release_expired_reservations
from payments.models import Purchase
from .serializers import ReserveSerializer


class AvailableNumbersAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, list_id):
        raffle_list = get_object_or_404(RaffleList, id=list_id)
        release_expired_reservations(raffle_id=raffle_list.raffle_id)

        numbers = raffle_list.numbers.filter(
            is_sold=False,
            is_reserved=False
        ).values_list('number', flat=True)

        return Response({
            "list": raffle_list.name,
            "available_numbers": list(numbers)
        })


class ReserveNumbersAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        if hasattr(request.data, 'getlist') and not payload.get('numbers') and request.data.getlist('numbers[]'):
            payload.setlist('numbers', request.data.getlist('numbers[]'))

        serializer = ReserveSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        raffle_id = data['raffle_id']
        numbers_requested = data['numbers']
        release_expired_reservations(raffle_id=raffle_id)

        raffle = get_object_or_404(Raffle, id=raffle_id)

        if not raffle.is_active or Draw.objects.filter(raffle_id=raffle_id).exists():
            return Response(
                {
                    "detail": "Esta rifa ya finalizó y no acepta más compras.",
                    "raffle_closed": True,
                },
                status=status.HTTP_409_CONFLICT,
            )

        amount = len(numbers_requested) * raffle.price_per_number

        purchase = None
        with transaction.atomic():
            purchase = Purchase.objects.create(
                user=request.user,
                raffle_id=raffle_id,
                amount=amount,
                reference=f"TIXI-{uuid.uuid4()}",
                status='pending'
            )

            raffle_numbers = RaffleNumber.objects.select_for_update().filter(
                raffle_list__raffle_id=raffle_id,
                number__in=numbers_requested,
                is_sold=False,
                is_reserved=False
            )

            if raffle_numbers.count() != len(numbers_requested):
                return Response({"detail": "One or more numbers are no longer available."}, status=status.HTTP_409_CONFLICT)

            for num in raffle_numbers:
                num.reserve(purchase)

        base_redirect = (settings.NGROK_URL or request.build_absolute_uri('/')).rstrip('/')
        return_url = f'{base_redirect}/payment/return?reference={purchase.reference}'
        webhook_url = f'{base_redirect}/webhook/wompi/'

        try:
            token_response = requests.post(
                "https://id.wompi.sv/connect/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.WOMPI_PUBLIC_KEY,
                    "client_secret": settings.WOMPI_API_SECRET,
                    "audience": "wompi_api",
                },
                timeout=20,
            )
        except requests.RequestException as error:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Error de conexión autenticando con Wompi.",
                    "wompi_error": str(error),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if token_response.status_code != 200:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "No se pudo autenticar con Wompi.",
                    "wompi_status": token_response.status_code,
                    "wompi_response": token_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            token_json = token_response.json()
        except ValueError:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Respuesta inválida de autenticación Wompi.",
                    "wompi_response": token_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        access_token = token_json.get("access_token")
        if not access_token:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Wompi no devolvió access_token.",
                    "wompi_response": token_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        wompi_payload = {
            "identificadorEnlaceComercio": purchase.reference,
            "monto": float(amount),
            "nombreProducto": raffle.title,
            "configuracion": {
                "urlRetorno": return_url,
                "urlWebhook": webhook_url,
            },
        }

        try:
            wompi_response = requests.post(
                "https://api.wompi.sv/EnlacePago",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=wompi_payload,
                timeout=20,
            )
        except requests.RequestException as error:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Error de conexión creando enlace en Wompi.",
                    "wompi_error": str(error),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if wompi_response.status_code not in (200, 201):
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "No se pudo crear el enlace de pago en Wompi.",
                    "wompi_status": wompi_response.status_code,
                    "wompi_response": wompi_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            wompi_data = wompi_response.json()
        except ValueError:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Respuesta inválida creando enlace en Wompi.",
                    "wompi_response": wompi_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        checkout_url = wompi_data.get("urlEnlace")

        if not checkout_url:
            release_reserved_numbers(purchase)
            purchase.status = 'failed'
            purchase.save(update_fields=['status'])
            return Response(
                {
                    "detail": "Wompi no devolvió urlEnlace.",
                    "wompi_response": wompi_data,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "purchase_id": purchase.id,
            "reference": purchase.reference,
            "checkout_url": checkout_url,
        }, status=status.HTTP_201_CREATED)
