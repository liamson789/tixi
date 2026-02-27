from django.utils import timezone

from .models import RaffleNumber

def finalize_raffle_numbers(purchase):
    """Marca como vendidas las `RaffleNumber` asociadas a una `Purchase`.

    Cambia `is_reserved` a False, `is_sold` a True y conserva la relación
    con la `purchase` para auditoría.
    """
    numbers = RaffleNumber.objects.filter(
        purchase=purchase,
        is_reserved=True,
        is_sold=False
    )

    numbers.update(
        is_reserved=False,
        is_sold=True,
        reserved_until=None
    )


def release_reserved_numbers(purchase):
    """Libera (des-reserva) los números reservados por una `Purchase` fallida.

    Quita la reserva y desvincula la `purchase`.
    """
    numbers = RaffleNumber.objects.filter(
        purchase=purchase,
        is_reserved=True,
        is_sold=False
    )

    numbers.update(
        is_reserved=False,
        reserved_until=None,
        purchase=None
    )


def release_expired_reservations(raffle_id=None):
    now = timezone.now()
    queryset = RaffleNumber.objects.filter(
        is_reserved=True,
        is_sold=False,
        reserved_until__lt=now,
    )

    if raffle_id is not None:
        queryset = queryset.filter(raffle_list__raffle_id=raffle_id)

    return queryset.update(
        is_reserved=False,
        reserved_until=None,
        purchase=None,
    )
