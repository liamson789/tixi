import hashlib
import random

from raffles.models import RaffleNumber


def execute_draw(raffle):
    seed = hashlib.sha256(str(raffle.id).encode()).hexdigest()
    random.seed(seed)

    sold_numbers = list(
        RaffleNumber.objects.filter(
            raffle_list__raffle=raffle,
            is_sold=True,
        ).values_list('number', flat=True)
    )

    if not sold_numbers:
        raise ValueError('No hay números vendidos para sortear en esta rifa.')

    winner_number = random.choice(sold_numbers)
    return seed, winner_number
import random, hashlib
from raffles.models import RaffleNumber

def execute_draw(raffle):
    seed = hashlib.sha256(str(raffle.id).encode()).hexdigest()
    random.seed(seed)

    sold = RaffleNumber.objects.filter(
        raffle_list__raffle=raffle,
        is_sold=True
    )

    winner = random.choice(list(sold))

    return seed, winner.number
    