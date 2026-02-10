from django.db import models
from django.contrib.auth.models import User

class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    raffle = models.ForeignKey('raffles.Raffle', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending','Pending'),
            ('paid','Paid'),
            ('failed','Failed')
        ],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
