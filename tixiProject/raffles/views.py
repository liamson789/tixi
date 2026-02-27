from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from .models import RaffleList, Raffle, RaffleNumber, HomeCarouselSlide
from draws.models import Draw
from django.db import transaction
from django.db.models import Max, Count, Q, Case, When, Value, IntegerField
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from payments.models import Purchase
import uuid
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .services import release_expired_reservations


def _mask_buyer_name(user):
    base_name = user.get_full_name().strip() or user.username or f"Usuario {user.id}"
    if len(base_name) <= 2:
        return "Usuario verificado"
    return f"{base_name[0]}{'*' * (len(base_name) - 2)}{base_name[-1]}"


def home(request):
    status_filter = request.GET.get('status', 'active')

    raffles_qs = (
        Raffle.objects
        .prefetch_related('media')
        .annotate(
            total_numbers=Count('lists__numbers', distinct=True),
            sold_numbers=Count('lists__numbers', filter=Q(lists__numbers__is_sold=True), distinct=True),
        )
        .order_by('-created_at')
    )

    featured_qs = (
        Raffle.objects
        .filter(is_active=True)
        .prefetch_related('media')
        .order_by('draw_date', '-created_at')
    )

    if status_filter == 'active':
        raffles_qs = raffles_qs.filter(is_active=True)

    raffle_items = []
    for raffle in raffles_qs:
        if raffle.total_numbers:
            sales_percentage = round((raffle.sold_numbers / raffle.total_numbers) * 100, 2)
        else:
            sales_percentage = 0
        raffle.sales_percentage = sales_percentage
        raffle_items.append(raffle)

    carousel_items = []

    slides = HomeCarouselSlide.objects.filter(is_active=True).order_by('display_order', '-created_at')[:8]
    for slide in slides:
        if slide.image:
            carousel_items.append({
                'title': slide.title,
                'subtitle': slide.subtitle,
                'image_url': slide.image.url,
                'target_url': slide.link_url or '#',
            })

    if not carousel_items:
        for raffle in featured_qs:
            cover = raffle.media.filter(media_type='image').first()
            if cover and cover.file:
                carousel_items.append({
                    'title': raffle.title,
                    'subtitle': f"Sorteo: {raffle.draw_date.strftime('%d/%m/%Y %H:%M')}",
                    'image_url': cover.file.url,
                    'target_url': reverse('raffle_detail', args=[raffle.id]),
                })
            if len(carousel_items) >= 5:
                break

    paginator = Paginator(raffle_items, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'raffles/home.html', {
        'raffles': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'carousel_items': carousel_items,
    })


def winners(request):
    draws = Draw.objects.select_related('raffle').order_by('-executed_at')

    winner_rows = []
    for draw in draws:
        winner_number = RaffleNumber.objects.filter(
            raffle_list__raffle=draw.raffle,
            number=draw.winner_number,
            is_sold=True,
            purchase__isnull=False,
        ).select_related('purchase__user', 'purchase__user__profile').first()

        buyer_alias = 'Usuario verificado'
        winner_name = 'Usuario verificado'
        winner_avatar_url = ''

        if winner_number and winner_number.purchase_id:
            buyer = winner_number.purchase.user
            buyer_alias = _mask_buyer_name(buyer)
            winner_name = buyer.get_full_name().strip() or buyer.username or 'Usuario verificado'
            winner_avatar_url = getattr(getattr(buyer, 'profile', None), 'avatar_url', '') or ''

        cleaned_comment = (draw.winner_comment or '').strip()

        winner_rows.append({
            'raffle_id': draw.raffle_id,
            'raffle_title': draw.raffle.title,
            'winner_number': draw.winner_number,
            'executed_at': draw.executed_at,
            'buyer_alias': buyer_alias,
            'winner_name': winner_name,
            'winner_avatar_url': winner_avatar_url,
            'winner_comment': cleaned_comment if draw.winner_comment_enabled and cleaned_comment else '',
            'winner_comment_exists': bool(cleaned_comment),
            'winner_comment_enabled': draw.winner_comment_enabled,
        })

    return render(request, 'raffles/winners.html', {
        'winner_rows': winner_rows,
    })

#ENDPOINT PARA VER NÚMEROS DISPONIBLES
def available_numbers(request, list_id):
    raffle_list = RaffleList.objects.get(id=list_id)

    numbers = raffle_list.numbers.filter(
        is_sold=False,
        is_reserved=False
    ).values_list('number', flat=True)

    return JsonResponse({
        "list": raffle_list.name,
        "available_numbers": list(numbers)
    })

@transaction.atomic
def reserve_numbers(request):
    user = request.user
    raffle_id = request.POST['raffle_id']
    numbers_requested = request.POST.getlist('numbers[]')

    raffle = Raffle.objects.get(id=raffle_id)
    amount = len(numbers_requested) * raffle.price_per_number

    purchase = Purchase.objects.create(
        user=user,
        raffle_id=raffle_id,
        amount=amount,
        reference=f"TIXI-{uuid.uuid4()}",
        status='pending'
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f'raffle_{raffle_id}',
        {
            "type": "send_update",
            "data": {
                "numbers": numbers_requested,
                "status": "reserved"
            }
        }
    )

    raffle_numbers = RaffleNumber.objects.select_for_update().filter(
        raffle_list__raffle_id=raffle_id,
        number__in=numbers_requested,
        is_sold=False,
        is_reserved=False
    )

    if raffle_numbers.count() != len(numbers_requested):
        raise Exception("Uno o más números ya no están disponibles")

    for num in raffle_numbers:
        num.reserve(purchase)

    return JsonResponse({
        "purchase_id": purchase.id,
        "reference": purchase.reference
    })

def raffle_detail(request, raffle_id):
    raffle = get_object_or_404(
        Raffle.objects.prefetch_related('media'),
        id=raffle_id,
    )
    release_expired_reservations(raffle_id=raffle.id)
    raffle_images = [media for media in raffle.media.all() if media.media_type == 'image']

    numbers = RaffleNumber.objects.filter(
        raffle_list__raffle=raffle
    ).values('number').annotate(
        is_sold=Max('is_sold'),
        is_reserved=Max('is_reserved'),
        reserved_until=Max('reserved_until'),
        is_mine=Max(
            Case(
                When(purchase__user=request.user, purchase__status='paid', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ) if request.user.is_authenticated else Value(0, output_field=IntegerField())
    ).order_by('number')

    numbers = list(numbers)
    total_numbers_count = len(numbers)
    sold_numbers_count = sum(1 for item in numbers if item['is_sold'])
    sold_percentage = round((sold_numbers_count / total_numbers_count) * 100, 1) if total_numbers_count else 0

    my_numbers = []
    if request.user.is_authenticated:
        my_numbers = list(
            RaffleNumber.objects.filter(
                raffle_list__raffle=raffle,
                purchase__user=request.user,
                purchase__status='paid',
                is_sold=True,
            )
            .values_list('number', flat=True)
            .distinct()
            .order_by('number')
        )

    latest_draw = Draw.objects.filter(raffle=raffle).order_by('-executed_at').first()
    public_draw_detail = None
    can_comment_as_winner = False
    winner_comment_value = ''
    winner_comment_enabled = False
    if latest_draw:
        winner_number = RaffleNumber.objects.filter(
            raffle_list__raffle=raffle,
            number=latest_draw.winner_number,
            is_sold=True,
            purchase__isnull=False,
        ).select_related('purchase__user', 'purchase__user__profile').first()

        buyer_alias = 'Usuario verificado'
        winner_name = 'Usuario verificado'
        winner_avatar_url = ''
        if winner_number and winner_number.purchase_id:
            buyer = winner_number.purchase.user
            buyer_alias = _mask_buyer_name(buyer)
            winner_name = buyer.get_full_name().strip() or buyer.username or 'Usuario verificado'
            winner_avatar_url = getattr(getattr(buyer, 'profile', None), 'avatar_url', '') or ''
            can_comment_as_winner = request.user.is_authenticated and buyer.id == request.user.id

        winner_comment_value = latest_draw.winner_comment
        winner_comment_enabled = latest_draw.winner_comment_enabled
        cleaned_comment = (latest_draw.winner_comment or '').strip()

        public_draw_detail = {
            'winner_number': latest_draw.winner_number,
            'executed_at': latest_draw.executed_at,
            'buyer_alias': buyer_alias,
            'winner_name': winner_name,
            'winner_avatar_url': winner_avatar_url,
            'winner_comment': cleaned_comment if latest_draw.winner_comment_enabled and cleaned_comment else '',
        }

    can_participate = raffle.is_active and public_draw_detail is None

    return render(request, 'raffles/raffle_detail.html', {
        'raffle': raffle,
        'numbers': numbers,
        'total_numbers_count': total_numbers_count,
        'sold_numbers_count': sold_numbers_count,
        'sold_percentage': sold_percentage,
        'my_numbers': my_numbers,
        'my_numbers_count': len(my_numbers),
        'raffle_images': raffle_images,
        'public_draw_detail': public_draw_detail,
        'can_participate': can_participate,
        'can_comment_as_winner': can_comment_as_winner,
        'winner_comment_value': winner_comment_value,
        'winner_comment_enabled': winner_comment_enabled,
    })


@login_required
@require_POST
def submit_winner_comment(request, raffle_id):
    raffle = get_object_or_404(Raffle, id=raffle_id)
    latest_draw = Draw.objects.filter(raffle=raffle).order_by('-executed_at').first()

    if not latest_draw:
        messages.error(request, 'No existe un sorteo ejecutado para esta rifa.')
        return redirect('raffle_detail', raffle_id=raffle_id)

    winner_number = RaffleNumber.objects.filter(
        raffle_list__raffle=raffle,
        number=latest_draw.winner_number,
        is_sold=True,
        purchase__isnull=False,
        purchase__user=request.user,
    ).first()

    if not winner_number:
        messages.error(request, 'Solo el ganador de esta rifa puede dejar un comentario.')
        return redirect('raffle_detail', raffle_id=raffle_id)

    winner_comment = request.POST.get('winner_comment', '').strip()
    latest_draw.winner_comment = winner_comment
    latest_draw.save(update_fields=['winner_comment'])

    messages.success(
        request,
        'Tu comentario fue guardado. Será visible cuando el administrador lo active.' if winner_comment else 'Tu comentario fue eliminado.',
    )
    return redirect('raffle_detail', raffle_id=raffle_id)


def raffle_status(request, raffle_id):
    raffle = get_object_or_404(Raffle, id=raffle_id)
    release_expired_reservations(raffle_id=raffle.id)
    reserved_by_me_expression = Value(0, output_field=IntegerField())
    if request.user.is_authenticated:
        reserved_by_me_expression = Max(
            Case(
                When(
                    is_reserved=True,
                    purchase__user=request.user,
                    then=Value(1)
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    numbers = RaffleNumber.objects.filter(
        raffle_list__raffle=raffle
    ).values('number').annotate(
        aggregated_is_reserved=Max('is_reserved'),
        aggregated_is_sold=Max('is_sold'),
        aggregated_reserved_until=Max('reserved_until'),
        is_reserved_by_me=reserved_by_me_expression,
        is_mine=Max(
            Case(
                When(purchase__user=request.user, purchase__status='paid', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ) if request.user.is_authenticated else Value(0, output_field=IntegerField())
    ).order_by('number')

    serialized_numbers = [
        {
            'number': item['number'],
            'is_reserved': item['aggregated_is_reserved'],
            'is_sold': item['aggregated_is_sold'],
            'reserved_until': item['aggregated_reserved_until'],
            'is_reserved_by_me': item['is_reserved_by_me'],
            'is_mine': item['is_mine'],
        }
        for item in numbers
    ]

    return JsonResponse(serialized_numbers, safe=False)

@login_required
@require_POST
@transaction.atomic
def reserve_numbers(request):
    raffle_id = request.POST['raffle_id']
    numbers_requested = request.POST.getlist('numbers[]')

    numbers = RaffleNumber.objects.select_for_update().filter(
        raffle_list__raffle_id=raffle_id,
        number__in=numbers_requested,
        is_sold=False,
        is_reserved=False
    )

    if numbers.count() != len(numbers_requested):
        return redirect('raffle_detail', raffle_id=raffle_id)

    for number in numbers:
        number.is_reserved = True
        number.user = request.user
        number.save()

    return redirect('checkout', raffle_id=raffle_id)
