from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import UserProfile
from payments.models import Purchase
from raffles.models import Raffle, RaffleList, RaffleNumber


class ProfileViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='normaluser',
			email='normal@example.com',
			password='testpass123',
		)

	def test_profile_requires_login(self):
		response = self.client.get(reverse('user_profile'))
		self.assertEqual(response.status_code, 302)

	def test_profile_updates_for_email_user(self):
		self.client.login(username='normaluser', password='testpass123')
		response = self.client.post(
			reverse('user_profile'),
			data={
				'full_name': 'Usuario Normal',
				'avatar_url': 'https://example.com/avatar.png',
			},
		)
		self.assertEqual(response.status_code, 200)

		profile = UserProfile.objects.get(user=self.user)
		self.assertEqual(profile.full_name, 'Usuario Normal')
		self.assertEqual(profile.avatar_url, 'https://example.com/avatar.png')

	def test_profile_does_not_update_for_google_profile(self):
		profile = UserProfile.objects.get(user=self.user)
		profile.auth_provider = 'google'
		profile.full_name = 'Nombre Original'
		profile.save()

		self.client.login(username='normaluser', password='testpass123')
		response = self.client.post(
			reverse('user_profile'),
			data={
				'full_name': 'Nombre Alterado',
				'avatar_url': 'https://example.com/new.png',
			},
		)
		self.assertEqual(response.status_code, 200)

		profile.refresh_from_db()
		self.assertEqual(profile.full_name, 'Nombre Original')

	def test_profile_shows_only_paid_purchases_with_raffle_progress(self):
		raffle = Raffle.objects.create(
			title='Rifa de prueba',
			description='Descripción',
			price_per_number=1.00,
			draw_date=timezone.now() + timezone.timedelta(days=1),
			min_sales_percentage=50,
		)
		raffle_list = RaffleList.objects.create(
			raffle=raffle,
			name='Lista principal',
			start_number=1,
			end_number=4,
		)

		paid_purchase = Purchase.objects.create(
			user=self.user,
			raffle=raffle,
			amount=4.00,
			reference='TIXI-PAID-123',
			status='paid',
		)
		pending_purchase = Purchase.objects.create(
			user=self.user,
			raffle=raffle,
			amount=4.00,
			reference='TIXI-PENDING-123',
			status='pending',
		)

		for number in range(1, 5):
			RaffleNumber.objects.create(
				raffle_list=raffle_list,
				number=number,
				is_sold=number <= 2,
				purchase=paid_purchase if number <= 2 else None,
			)

		self.client.login(username='normaluser', password='testpass123')
		response = self.client.get(reverse('user_profile'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, paid_purchase.reference)
		self.assertNotContains(response, pending_purchase.reference)

		user_purchases = response.context['user_purchases']
		self.assertEqual(len(user_purchases), 1)
		self.assertEqual(user_purchases[0].raffle_sold_percentage, 50.0)
		self.assertEqual(user_purchases[0].raffle_sold_numbers, 2)
		self.assertEqual(user_purchases[0].raffle_total_numbers, 4)
		self.assertEqual(user_purchases[0].purchased_numbers, [1, 2])
		self.assertTrue(user_purchases[0].has_user_numbers)

		participation_summary = response.context['participation_summary']
		self.assertEqual(len(participation_summary), 1)
		self.assertEqual(participation_summary[0]['count'], 2)
		self.assertEqual(response.context['total_participating_numbers'], 2)
