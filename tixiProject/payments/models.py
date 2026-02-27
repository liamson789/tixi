from django.db import models
from django.contrib.auth.models import User
import requests
from django.conf import settings
import json


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

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    raffle = models.ForeignKey('raffles.Raffle', on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def verify_transaction(self):
        """Verifica el estado de la transacción en Wompi"""
        response = requests.get(
            f"https://api.wompi.sv/transaccion/{self.transaction_id}",
            headers={
                "Authorization": f"Bearer {settings.WOMPI_API_SECRET}"
            }
        )
        return response.json()


class WebhookLog(models.Model):
    """Modelo para auditar y debuggear webhooks de Wompi"""
    
    STATUS_CHOICES = [
        ('received', 'Recibido'),
        ('valid', 'Válido'),
        ('invalid_signature', 'Firma inválida'),
        ('invalid_json', 'JSON inválido'),
        ('missing_reference', 'Reference faltante'),
        ('purchase_not_found', 'Purchase no encontrada'),
        ('processed', 'Procesado'),
        ('error', 'Error'),
    ]
    
    # Campos del webhook
    payload = models.JSONField(help_text="Payload completo del webhook")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='received')
    reference = models.CharField(max_length=100, null=True, blank=True)
    resultado_transaccion = models.CharField(max_length=50, null=True, blank=True)
    
    # Validación
    signature_valid = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
    
    def __str__(self):
        return f"Webhook {self.reference} - {self.get_status_display()} ({self.received_at})"
