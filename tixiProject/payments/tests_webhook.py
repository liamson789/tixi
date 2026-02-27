"""
Tests para el webhook de Wompi
"""
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from raffles.models import Raffle, RaffleList, RaffleNumber
from payments.models import Purchase
from datetime import datetime, timedelta


class WompiWebhookTestCase(TestCase):
    """Tests para el endpoint /webhook/wompi/"""
    
    def setUp(self):
        """Preparar datos de prueba"""
        self.client = Client()
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear rifa
        self.raffle = Raffle.objects.create(
            title='Test Raffle',
            description='Rifa de prueba',
            price_per_number=1.00,
            draw_date=datetime.now() + timedelta(days=1),
            min_sales_percentage=50
        )
        
        # Crear lista de números
        self.raffle_list = RaffleList.objects.create(
            raffle=self.raffle,
            name='List 1',
            start_number=1,
            end_number=100
        )
        
        # Crear Purchase
        self.purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=10.00,
            reference='TEST-REF-001',
            status='pending'
        )
    
    def test_webhook_success_payment(self):
        """Test: Webhook recibe pago aprobado (ExitosaAprobada)"""
        payload = {
            "ResultadoTransaccion": "ExitosaAprobada",
            "EnlacePago": {
                "IdentificadorEnlaceComercio": "TEST-REF-001",
                "Monto": 10.00
            }
        }
        
        response = self.client.post(
            '/webhook/wompi/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        
        # Verificar que Purchase se actualizó
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, 'paid')
    
    def test_webhook_failed_payment(self):
        """Test: Webhook recibe pago rechazado"""
        payload = {
            "ResultadoTransaccion": "Rechazada",
            "EnlacePago": {
                "IdentificadorEnlaceComercio": "TEST-REF-001"
            }
        }
        
        response = self.client.post(
            '/webhook/wompi/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, 'failed')
    
    def test_webhook_missing_reference(self):
        """Test: Webhook sin reference debería retornar 400"""
        payload = {
            "ResultadoTransaccion": "ExitosaAprobada",
            "EnlacePago": {}
        }
        
        response = self.client.post(
            '/webhook/wompi/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_webhook_purchase_not_found(self):
        """Test: Webhook con reference inexistente debería retornar 404"""
        payload = {
            "ResultadoTransaccion": "ExitosaAprobada",
            "EnlacePago": {
                "IdentificadorEnlaceComercio": "INVALID-REF"
            }
        }
        
        response = self.client.post(
            '/webhook/wompi/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_webhook_invalid_json(self):
        """Test: Webhook con JSON inválido debería retornar 400"""
        response = self.client.post(
            '/webhook/wompi/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_webhook_invalid_content_type(self):
        """Test: Webhook sin Content-Type correcto debería retornar 400"""
        response = self.client.post(
            '/webhook/wompi/',
            data='test',
            content_type='text/plain'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_webhook_wrong_method(self):
        """Test: GET en webhook debería retornar 405"""
        response = self.client.get('/webhook/wompi/')
        
        self.assertEqual(response.status_code, 405)


if __name__ == '__main__':
    import unittest
    unittest.main()
