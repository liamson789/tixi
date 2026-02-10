from django.db import models
from django.utils import timezone

#Rifas
class Raffle(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price_per_number = models.DecimalField(max_digits=8, decimal_places=2)
    draw_date = models.DateTimeField()
    min_sales_percentage = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

#Listas
class RaffleList(models.Model):
    raffle = models.ForeignKey(Raffle, related_name='lists', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_number = models.PositiveIntegerField()
    end_number = models.PositiveIntegerField()

#Numeros


class RaffleNumber(models.Model):
    raffle_list = models.ForeignKey(
        'RaffleList',
        related_name='numbers',
        on_delete=models.CASCADE
    )
    number = models.PositiveIntegerField()

    is_reserved = models.BooleanField(default=False)
    reserved_until = models.DateTimeField(null=True, blank=True)

    is_sold = models.BooleanField(default=False)

    purchase = models.ForeignKey(
        'payments.Purchase',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def reserve(self, purchase):
        self.is_reserved = True
        self.purchase = purchase
        self.reserved_until = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
