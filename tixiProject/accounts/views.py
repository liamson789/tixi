from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.db.models import Count, Q, Prefetch
from collections import defaultdict

from .forms import UserProfileForm
from .models import UserProfile
from payments.models import Purchase
from raffles.models import RaffleMedia, RaffleNumber
from draws.models import Draw


def _safe_reverse(name):
	try:
		return reverse(name)
	except NoReverseMatch:
		return None


@login_required
def profile_view(request):
	profile, _ = UserProfile.objects.get_or_create(user=request.user)
	is_google_profile = profile.auth_provider == 'google'
	user_purchases = list(
		Purchase.objects.filter(user=request.user, status='paid')
		.select_related('raffle')
		.prefetch_related(
			Prefetch(
				'raffle__media',
				queryset=RaffleMedia.objects.filter(media_type='image').order_by('-uploaded_at'),
				to_attr='profile_images',
			),
			Prefetch(
				'rafflenumber_set',
				queryset=RaffleNumber.objects.select_related('raffle_list').order_by('number'),
			)
		)
		.annotate(numbers_count=Count('rafflenumber'))
		.order_by('-created_at')
	)

	raffle_ids = [purchase.raffle_id for purchase in user_purchases]
	latest_draw_by_raffle = {}
	if raffle_ids:
		draws = Draw.objects.filter(raffle_id__in=raffle_ids).order_by('raffle_id', '-executed_at')
		for draw in draws:
			if draw.raffle_id not in latest_draw_by_raffle:
				latest_draw_by_raffle[draw.raffle_id] = draw

	raffle_stats = {
		item['raffle_list__raffle_id']: item
		for item in RaffleNumber.objects.filter(raffle_list__raffle_id__in=raffle_ids)
		.values('raffle_list__raffle_id')
		.annotate(
			total_numbers=Count('id'),
			sold_numbers=Count('id', filter=Q(is_sold=True)),
		)
	}

	participation_summary_by_raffle = defaultdict(lambda: {'raffle': None, 'count': 0})
	total_participating_numbers = 0

	for purchase in user_purchases:
		stats = raffle_stats.get(purchase.raffle_id, {})
		total_numbers = stats.get('total_numbers', 0)
		sold_numbers = stats.get('sold_numbers', 0)
		purchase.raffle_total_numbers = total_numbers
		purchase.raffle_sold_numbers = sold_numbers
		purchase.raffle_sold_percentage = round((sold_numbers / total_numbers) * 100, 2) if total_numbers else 0
		purchase.purchased_numbers = [num.number for num in purchase.rafflenumber_set.all()]
		purchase.has_user_numbers = bool(purchase.purchased_numbers)
		draw = latest_draw_by_raffle.get(purchase.raffle_id)
		purchase.is_winner = bool(draw and draw.winner_number in purchase.purchased_numbers)
		purchase.winner_number = draw.winner_number if draw else None

		raffle_images = getattr(purchase.raffle, 'profile_images', [])
		purchase.raffle_image_url = raffle_images[0].file.url if raffle_images else None

		if purchase.has_user_numbers:
			participation_summary_by_raffle[purchase.raffle_id]['raffle'] = purchase.raffle
			participation_summary_by_raffle[purchase.raffle_id]['count'] += len(purchase.purchased_numbers)
			total_participating_numbers += len(purchase.purchased_numbers)

	participation_summary = sorted(
		participation_summary_by_raffle.values(),
		key=lambda item: item['count'],
		reverse=True,
	)

	account_links = {
		'change_password': _safe_reverse('account_change_password'),
		'set_password': _safe_reverse('account_set_password'),
		'manage_email': _safe_reverse('account_email'),
		'logout': _safe_reverse('account_logout'),
	}

	if request.method == 'POST':
		form = UserProfileForm(request.POST, instance=profile, is_google_profile=is_google_profile)
		if form.is_valid():
			form.save()
			if is_google_profile:
				messages.success(request, 'Datos de contacto actualizados. Nombre y foto se sincronizan con Google.')
			else:
				messages.success(request, 'Perfil actualizado correctamente.')
		else:
			messages.error(request, 'Revisa los campos del perfil.')
		return render(
			request,
			'accounts/profile.html',
			{
				'profile': profile,
				'profile_form': form,
				'is_google_profile': is_google_profile,
				'account_links': account_links,
				'user_purchases': user_purchases,
				'participation_summary': participation_summary,
				'total_participating_numbers': total_participating_numbers,
			},
		)

	form = UserProfileForm(instance=profile, is_google_profile=is_google_profile)
	return render(
		request,
		'accounts/profile.html',
		{
			'profile': profile,
			'profile_form': form,
			'is_google_profile': is_google_profile,
			'account_links': account_links,
			'user_purchases': user_purchases,
			'participation_summary': participation_summary,
			'total_participating_numbers': total_participating_numbers,
		},
	)
