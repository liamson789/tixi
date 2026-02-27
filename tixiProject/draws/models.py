from django.db import models
from raffles.models import Raffle

# Create your models here.
class Draw(models.Model):
    raffle = models.ForeignKey(Raffle, on_delete=models.CASCADE)
    #raffle = models.OneToOneField(Raffle, on_delete=models.CASCADE)
    seed = models.CharField(max_length=255)
    winner_number = models.PositiveIntegerField()
    winner_comment = models.TextField(blank=True)
    winner_comment_enabled = models.BooleanField(default=False)
    executed_at = models.DateTimeField(auto_now_add=True)
