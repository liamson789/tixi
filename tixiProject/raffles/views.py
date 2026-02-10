from django.shortcuts import render
from django.http import JsonResponse
from .models import RaffleList, Raffle, RaffleNumber
from django.db import transaction
from django.utils import timezone
from payments.models import Purchase
import uuid
#Frontend solo muestra lo que el backend dice
def available_numbers(request, list_id):
    raffle_list = RaffleList.objects.get(id=list_id)

    numbers = raffle_list.numbers.filter(
        is_sold=False,
        is_reserved=False
    ).values_list('number', flat=True)

    return JsonResponse({
        "list": raffle_list.name,
        "available_numbers": list(numbers)
    })

@transaction.atomic
def reserve_numbers(request):
    user = request.user
    raffle_id = request.POST['raffle_id']
    numbers_requested = request.POST.getlist('numbers[]')

    raffle = Raffle.objects.get(id=raffle_id)
    amount = len(numbers_requested) * raffle.price_per_number

    purchase = Purchase.objects.create(
        user=user,
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
        raise Exception("Uno o más números ya no están disponibles")

    for num in raffle_numbers:
        num.reserve(purchase)

    return JsonResponse({
        "purchase_id": purchase.id,
        "reference": purchase.reference
    })

