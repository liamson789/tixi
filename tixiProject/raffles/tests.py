from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import json
import uuid

from .models import Raffle, RaffleList, RaffleNumber
from payments.models import Purchase
from raffles.services import finalize_raffle_numbers, release_reserved_numbers

from rest_framework.test import APIClient


class RaffleReservationTestCase(TestCase):
    """Prueba completa del flujo: reservar números → pago exitoso → números vendidos"""

    def setUp(self):
        """Configurar fixtures de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Crear una rifa
        self.raffle = Raffle.objects.create(
            title='Rifa Test',
            description='Rifa para pruebas',
            price_per_number=Decimal('10.00'),
            draw_date=timezone.now() + timedelta(days=30),
            min_sales_percentage=50,
            is_active=True
        )

        # Crear lista de números
        self.raffle_list = RaffleList.objects.create(
            raffle=self.raffle,
            name='Lista 1-100',
            start_number=1,
            end_number=100
        )

        # Crear números del 1 al 100
        for i in range(1, 101):
            RaffleNumber.objects.create(
                raffle_list=self.raffle_list,
                number=i
            )

    def test_reserve_numbers_success(self):
        """Prueba: Reservar números exitosamente"""
        numbers_to_reserve = [1, 2, 3]
        
        # Crear Purchase
        purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=Decimal('30.00'),
            reference=f"TIXI-{uuid.uuid4()}",
            status='pending'
        )

        # Reservar números
        reserved_numbers = RaffleNumber.objects.filter(
            raffle_list=self.raffle_list,
            number__in=numbers_to_reserve
        )

        self.assertEqual(reserved_numbers.count(), 3, "Debe haber 3 números disponibles para reservar")

        for num in reserved_numbers:
            num.reserve(purchase)

        # Verificar que se reservaron correctamente
        for num in reserved_numbers:
            num.refresh_from_db()
            self.assertTrue(num.is_reserved, f"Número {num.number} debe estar reservado")
            self.assertFalse(num.is_sold, f"Número {num.number} no debe estar vendido aún")
            self.assertEqual(num.purchase, purchase, f"Número {num.number} debe estar vinculado a la Purchase")
            self.assertIsNotNone(num.reserved_until, f"Número {num.number} debe tener reserved_until")

    def test_finalize_raffle_numbers_on_successful_payment(self):
        """Prueba: Al pago exitoso, los números se marcan como vendidos"""
        numbers_to_reserve = [10, 11, 12]

        # Crear y reservar una Purchase
        purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=Decimal('30.00'),
            reference=f"TIXI-{uuid.uuid4()}",
            status='pending'
        )

        reserved_numbers = RaffleNumber.objects.filter(
            raffle_list=self.raffle_list,
            number__in=numbers_to_reserve
        )

        for num in reserved_numbers:
            num.reserve(purchase)

        # Simular pago exitoso
        purchase.status = 'paid'
        purchase.save()
        finalize_raffle_numbers(purchase)

        # Verificar que se finalizaron correctamente
        for num in reserved_numbers:
            num.refresh_from_db()
            self.assertFalse(num.is_reserved, f"Número {num.number} no debe estar reservado después de finalizar")
            self.assertTrue(num.is_sold, f"Número {num.number} debe estar vendido después de finalizar")
            self.assertIsNone(num.reserved_until, f"Número {num.number} debe tener reserved_until=None")
            self.assertEqual(num.purchase, purchase, f"Número {num.number} debe seguir vinculado a la Purchase")

    def test_release_reserved_numbers_on_failed_payment(self):
        """Prueba: Al fallo de pago, los números se liberan y desvinculan"""
        numbers_to_reserve = [20, 21, 22]

        # Crear y reservar una Purchase
        purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=Decimal('30.00'),
            reference=f"TIXI-{uuid.uuid4()}",
            status='pending'
        )

        reserved_numbers = RaffleNumber.objects.filter(
            raffle_list=self.raffle_list,
            number__in=numbers_to_reserve
        )

        for num in reserved_numbers:
            num.reserve(purchase)

        # Simular fallo de pago
        purchase.status = 'failed'
        purchase.save()
        release_reserved_numbers(purchase)

        # Verificar que se liberaron correctamente
        for num in reserved_numbers:
            num.refresh_from_db()
            self.assertFalse(num.is_reserved, f"Número {num.number} debe estar des-reservado después de fallo de pago")
            self.assertFalse(num.is_sold, f"Número {num.number} no debe estar vendido")
            self.assertIsNone(num.reserved_until, f"Número {num.number} debe tener reserved_until=None")
            self.assertIsNone(num.purchase, f"Número {num.number} debe desvincularse de la Purchase")

    def test_full_flow_success_payment(self):
        """Prueba: Flujo completo exitoso (reservar → pago → números vendidos)"""
        numbers = [30, 31, 32, 33]

        # 1. Reservar números
        purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=Decimal('40.00'),
            reference=f"TIXI-{uuid.uuid4()}",
            status='pending'
        )

        for num_id in numbers:
            num = RaffleNumber.objects.get(raffle_list=self.raffle_list, number=num_id)
            num.reserve(purchase)

        # 2. Simular webhook de pago exitoso
        finalize_raffle_numbers(purchase)
        purchase.status = 'paid'
        purchase.save()

        # 3. Verificar que todo se finalizó correctamente
        sold_numbers = RaffleNumber.objects.filter(
            raffle_list=self.raffle_list,
            number__in=numbers
        )

        for num in sold_numbers:
            self.assertTrue(num.is_sold, "Los números deben estar vendidos")
            self.assertFalse(num.is_reserved, "Los números no deben estar reservados")
            self.assertEqual(num.purchase, purchase, "Todos deben estar vinculados a la compra")

    def test_full_flow_failed_payment(self):
        """Prueba: Flujo completo fallido (reservar → pago falla → números liberados)"""
        numbers = [40, 41, 42]

        # 1. Reservar números
        purchase = Purchase.objects.create(
            user=self.user,
            raffle=self.raffle,
            amount=Decimal('30.00'),
            reference=f"TIXI-{uuid.uuid4()}",
            status='pending'
        )

        for num_id in numbers:
            num = RaffleNumber.objects.get(raffle_list=self.raffle_list, number=num_id)
            num.reserve(purchase)

        # 2. Simular webhook de pago fallido
        release_reserved_numbers(purchase)
        purchase.status = 'failed'
        purchase.save()

        # 3. Verificar que se liberaron correctamente
        released_numbers = RaffleNumber.objects.filter(
            raffle_list=self.raffle_list,
            number__in=numbers
        )

        for num in released_numbers:
            self.assertFalse(num.is_sold, "Los números no deben estar vendidos")
            self.assertFalse(num.is_reserved, "Los números deben estar des-reservados")
            self.assertIsNone(num.purchase, "Los números deben desvincularse de la compra")
            # Ahora deben estar disponibles nuevamente
            self.assertTrue(
                not num.is_reserved and not num.is_sold,
                "Los números deben estar disponibles nuevamente"
            )

        def test_api_available_numbers(self):
            client = APIClient()
            # Create some reserved numbers to ensure filtering
            # Reserve 1 and 2
            purchase = Purchase.objects.create(
                user=self.user,
                raffle=self.raffle,
                amount=Decimal('20.00'),
                reference=f"TIXI-{uuid.uuid4()}",
                status='pending'
            )
            for n in [1, 2]:
                num = RaffleNumber.objects.get(raffle_list=self.raffle_list, number=n)
                num.reserve(purchase)

            resp = client.get(f"/api/lists/{self.raffle_list.id}/available/")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('available_numbers', data)
            self.assertNotIn(1, data['available_numbers'])

        def test_api_reserve_numbers_authenticated(self):
            client = APIClient()
            client.force_authenticate(user=self.user)

            payload = {
                'raffle_id': self.raffle.id,
                'numbers': [50, 51]
            }

            resp = client.post('/api/reserve/', payload, format='json')
            self.assertIn(resp.status_code, (201, 200))
            data = resp.json()
            self.assertIn('purchase_id', data)
