import uuid
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import RaffleList, RaffleNumber, Raffle
from payments.models import Purchase
from .serializers import ReserveSerializer


class AvailableNumbersAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, list_id):
        raffle_list = get_object_or_404(RaffleList, id=list_id)

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

    @transaction.atomic
    def post(self, request):
        serializer = ReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        raffle_id = data['raffle_id']
        numbers_requested = data['numbers']

        raffle = get_object_or_404(Raffle, id=raffle_id)

        amount = len(numbers_requested) * raffle.price_per_number

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

        return Response({
            "purchase_id": purchase.id,
            "reference": purchase.reference
        }, status=status.HTTP_201_CREATED)
