from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from raffles.models import Raffle, RaffleNumber, RaffleList, RaffleMedia, HomeCarouselSlide
from draws.models import Draw
from accounts.models import UserProfile
from payments.models import Purchase
from .forms import RaffleForm, RaffleCreateForm, RaffleEditForm, CarouselSlideForm
from django.db.models import Count, Sum, Q, F, DecimalField, ExpressionWrapper
from django.utils import timezone


def _mask_buyer_name(user):
    base_name = user.get_full_name().strip() or user.username or f"Usuario {user.id}"
    if len(base_name) <= 2:
        return "Usuario verificado"
    return f"{base_name[0]}{'*' * (len(base_name) - 2)}{base_name[-1]}"


def _safe_file_url(file_field):
    try:
        return file_field.url if file_field else ''
    except Exception:
        return ''


def _safe_avatar_url(user_id):
    try:
        return UserProfile.objects.filter(user_id=user_id).values_list('avatar_url', flat=True).first() or ''
    except Exception:
        return ''


def _get_draw_winner_detail(draw):
    winner_number = RaffleNumber.objects.filter(
        raffle_list__raffle_id=draw.raffle_id,
        number=draw.winner_number,
        is_sold=True,
        purchase__isnull=False,
    ).select_related('purchase__user').first()

    if not winner_number or not winner_number.purchase_id:
        return {
            'draw': draw,
            'buyer_name': 'No disponible',
            'buyer_alias': 'Usuario verificado',
            'buyer_email': 'No disponible',
            'buyer_avatar_url': '',
            'buyer_user_id': None,
            'purchase_reference': 'No disponible',
            'purchase_date': None,
        }

    buyer = winner_number.purchase.user
    buyer_name = buyer.get_full_name().strip() or buyer.username

    return {
        'draw': draw,
        'buyer_name': buyer_name,
        'buyer_alias': _mask_buyer_name(buyer),
        'buyer_email': buyer.email or 'No disponible',
        'buyer_avatar_url': _safe_avatar_url(buyer.id),
        'buyer_user_id': buyer.id,
        'purchase_reference': winner_number.purchase.reference,
        'purchase_date': winner_number.purchase.created_at,
    }


def _save_raffle_media_from_files(raffle, files):
    media_count = 0
    unsupported_count = 0
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    video_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']

    for file in files:
        file_extension = file.name.split('.')[-1].lower()
        if file_extension in image_extensions:
            RaffleMedia.objects.create(
                raffle=raffle,
                file=file,
                media_type='image'
            )
            media_count += 1
        elif file_extension in video_extensions:
            RaffleMedia.objects.create(
                raffle=raffle,
                file=file,
                media_type='video'
            )
            media_count += 1
        else:
            unsupported_count += 1

    return media_count, unsupported_count


@staff_member_required
def create_raffle(request):
    if request.method == 'POST':
        form = RaffleCreateForm(request.POST, request.FILES)
        if form.is_valid():
            raffle = form.save()
            list_name = form.cleaned_data['list_name']
            list_start = form.cleaned_data['list_start']
            list_end = form.cleaned_data['list_end']

            raffle_list = RaffleList.objects.create(
                raffle=raffle,
                name=list_name,
                start_number=list_start,
                end_number=list_end
            )

            numbers = [
                RaffleNumber(
                    raffle_list=raffle_list,
                    number=n
                )
                for n in range(list_start, list_end + 1)
            ]
            RaffleNumber.objects.bulk_create(numbers)

            files = request.FILES.getlist('media_files')
            media_count, unsupported_count = _save_raffle_media_from_files(raffle, files)

            if media_count > 0 and unsupported_count > 0:
                messages.warning(
                    request,
                    f'Rifa creada. Se subieron {media_count} archivo(s). {unsupported_count} no fueron soportados.'
                )
            elif media_count > 0:
                messages.success(request, f'Rifa creada con {media_count} archivo(s).')
            elif unsupported_count > 0:
                messages.warning(request, 'Rifa creada pero los archivos no son soportados.')
            else:
                messages.success(request, 'Rifa creada correctamente.')
            return redirect('dashboard:raffle_detail', raffle.id)
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = RaffleCreateForm()

    return render(request, 'dashboard/raffle_create.html', {'form': form})

@staff_member_required
def add_list(request, raffle_id):
    try:
        raffle = Raffle.objects.get(id=raffle_id)
    except Raffle.DoesNotExist:
        return redirect('dashboard:home')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            start = int(request.POST.get('start', 0))
            end = int(request.POST.get('end', 0))

            # Validar que los números sean válidos
            if start < 0 or end < 0 or start > end:
                messages.error(request, 'Los números deben ser válidos y el número inicial debe ser menor que el final.')
                return render(request, 'dashboard/add_list.html', {'raffle': raffle})

            overlap_exists = RaffleNumber.objects.filter(
                raffle_list__raffle=raffle,
                number__gte=start,
                number__lte=end,
            ).exists()

            if overlap_exists:
                messages.error(
                    request,
                    'Ese rango se superpone con números ya existentes en esta rifa. Usa un rango diferente.'
                )
                return render(request, 'dashboard/add_list.html', {'raffle': raffle})

            # Crear lista de números
            raffle_list = RaffleList.objects.create(
                raffle=raffle,
                name=name,
                start_number=start,
                end_number=end
            )
            
            # Crear números secuenciales
            numbers = [
                RaffleNumber(
                    raffle_list=raffle_list,
                    number=n
                )
                for n in range(start, end + 1)
            ]
            RaffleNumber.objects.bulk_create(numbers)

            messages.success(request, f'Lista "{name}" creada exitosamente con {end - start + 1} numeros.')
            
            return redirect('dashboard:raffle_detail', raffle_id=raffle.id)

        except ValueError:
            messages.error(request, 'Por favor ingresa números válidos.')
            return render(request, 'dashboard/add_list.html', {'raffle': raffle})

    return render(request, 'dashboard/add_list.html', {'raffle': raffle})

@staff_member_required
def raffle_detail(request, raffle_id):
    raffle = Raffle.objects.get(id=raffle_id)

    raffle_lists = raffle.lists.annotate(
        total_numbers=Count('numbers'),
        sold_numbers=Count('numbers', filter=Q(numbers__is_sold=True)),
        reserved_numbers=Count(
            'numbers',
            filter=Q(numbers__is_reserved=True, numbers__is_sold=False)
        )
    )

    numbers_qs = RaffleNumber.objects.filter(
        raffle_list__raffle=raffle
    )

    sold = numbers_qs.filter(
        is_sold=True
    ).count()

    reserved = numbers_qs.filter(
        is_reserved=True,
        is_sold=False
    ).count()

    total = numbers_qs.count()

    percentage = (sold / total) * 100 if total else 0
    available = total - sold - reserved
    remaining_percentage = max(0, raffle.min_sales_percentage - percentage)
    latest_draw = Draw.objects.filter(raffle=raffle).order_by('-executed_at').first()
    latest_draw_detail = _get_draw_winner_detail(latest_draw) if latest_draw else None

    return render(request, 'dashboard/raffle_detail.html', {
        'raffle': raffle,
        'raffle_lists': raffle_lists,
        'sold': sold,
        'reserved': reserved,
        'total': total,
        'available': available,
        'percentage': percentage,
        'remaining_percentage': remaining_percentage,
        'latest_draw_detail': latest_draw_detail,
    })


@staff_member_required
def toggle_winner_comment(request, raffle_id):
    if request.method != 'POST':
        return redirect('dashboard:raffle_detail', raffle_id=raffle_id)

    raffle = get_object_or_404(Raffle, id=raffle_id)
    latest_draw = Draw.objects.filter(raffle=raffle).order_by('-executed_at').first()

    if not latest_draw:
        messages.error(request, 'No existe un sorteo para esta rifa.')
        return redirect('dashboard:raffle_detail', raffle_id=raffle_id)

    if not (latest_draw.winner_comment or '').strip():
        latest_draw.winner_comment_enabled = False
        latest_draw.save(update_fields=['winner_comment_enabled'])
        messages.warning(request, 'No hay comentario del ganador para activar.')
        return redirect('dashboard:raffle_detail', raffle_id=raffle_id)

    latest_draw.winner_comment_enabled = request.POST.get('winner_comment_enabled') == 'on'
    latest_draw.save(update_fields=['winner_comment_enabled'])

    if latest_draw.winner_comment_enabled:
        messages.success(request, 'Comentario del ganador activado para vista pública.')
    else:
        messages.success(request, 'Comentario del ganador desactivado de la vista pública.')

    return redirect('dashboard:raffle_detail', raffle_id=raffle_id)



@staff_member_required
def manual_draw(request, raffle_id):
    from draws.services import execute_draw

    try:
        raffle = Raffle.objects.get(id=raffle_id)
    except Raffle.DoesNotExist:
        messages.error(request, 'La rifa no existe.')
        return redirect('dashboard:home')

    try:
        seed, winner_number = execute_draw(raffle)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('dashboard:raffle_detail', raffle.id)

    Draw.objects.create(
        raffle=raffle,
        seed=seed,
        winner_number=winner_number
    )

    raffle.is_active = False
    raffle.save()

    return redirect('dashboard:raffle_detail', raffle.id)


@staff_member_required
def edit_raffle(request, raffle_id):
    try:
        raffle = Raffle.objects.get(id=raffle_id)
    except Raffle.DoesNotExist:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = RaffleEditForm(request.POST, request.FILES, instance=raffle)
        if form.is_valid():
            form.save()
            files = request.FILES.getlist('media_files')
            media_count, unsupported_count = _save_raffle_media_from_files(raffle, files)

            if media_count > 0 and unsupported_count > 0:
                messages.warning(
                    request,
                    f'Rifa actualizada. Se subieron {media_count} archivo(s). {unsupported_count} no fueron soportados.'
                )
            elif media_count > 0:
                messages.success(request, f'Rifa actualizada con {media_count} archivo(s) nuevos.')
            elif unsupported_count > 0:
                messages.warning(request, 'Rifa actualizada, pero algunos archivos no son soportados.')
            else:
                messages.success(request, 'Rifa actualizada correctamente.')

            return redirect('dashboard:raffle_detail', raffle.id)
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = RaffleEditForm(instance=raffle)

    return render(request, 'dashboard/raffle_form.html', {
        'form': form,
        'raffle': raffle,
        'is_edit': True
    })


@staff_member_required
def delete_raffle(request, raffle_id):
    try:
        raffle = Raffle.objects.get(id=raffle_id)
    except Raffle.DoesNotExist:
        return redirect('dashboard:home')

    if request.method == 'POST':
        raffle_title = raffle.title
        raffle.delete()
        messages.success(request, f'Rifa "{raffle_title}" eliminada correctamente.')
        return redirect('dashboard:home')

    return render(request, 'dashboard/raffle_confirm_delete.html', {'raffle': raffle})


@staff_member_required
def edit_list(request, list_id):
    try:
        raffle_list = RaffleList.objects.get(id=list_id)
    except RaffleList.DoesNotExist:
        return redirect('dashboard:home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, 'El nombre de la lista es requerido.')
            return render(request, 'dashboard/list_form.html', {'list': raffle_list, 'is_edit': True})
        
        raffle_list.name = name
        raffle_list.save()
        
        messages.success(request, 'Lista actualizada.')
        
        return redirect('dashboard:raffle_detail', raffle_list.raffle.id)

    return render(request, 'dashboard/list_form.html', {
        'list': raffle_list,
        'raffle': raffle_list.raffle,
        'is_edit': True
    })


@staff_member_required
def delete_list(request, list_id):
    try:
        raffle_list = RaffleList.objects.get(id=list_id)
    except RaffleList.DoesNotExist:
        return redirect('dashboard:home')

    raffle_id = raffle_list.raffle.id

    if request.method == 'POST':
        list_name = raffle_list.name
        raffle_list.delete()
        messages.success(request, f'Lista "{list_name}" eliminada correctamente.')
        return redirect('dashboard:raffle_detail', raffle_id)

    return render(request, 'dashboard/list_confirm_delete.html', {
        'list': raffle_list,
        'raffle': raffle_list.raffle
    })


@staff_member_required
def delete_raffle_media(request, media_id):
    try:
        media = RaffleMedia.objects.get(id=media_id)
    except RaffleMedia.DoesNotExist:
        return redirect('dashboard:home')

    raffle_id = media.raffle.id
    
    if request.method == 'POST':
        media.delete()
        messages.success(request, 'Archivo eliminado correctamente.')
    
    return redirect('dashboard:raffle_detail', raffle_id)


@staff_member_required

def draw_history(request):
    draws = Draw.objects.all().order_by('-executed_at')
    draw_details = [_get_draw_winner_detail(draw) for draw in draws]

    return render(request, 'dashboard/draw_history.html', {'draw_details': draw_details})


def dashboard_home(request):

    raffles = Raffle.objects.all().order_by('draw_date')

    draw_filter = request.GET.get('draw_filter', 'all_upcoming')
    valid_draw_filters = {'next_7', 'next_30', 'all_upcoming'}
    if draw_filter not in valid_draw_filters:
        draw_filter = 'all_upcoming'

    now = timezone.now()
    days_by_filter = {
        'next_7': 7,
        'next_30': 30,
    }

    raffle_data = []
    eligible_for_draw = []
    upcoming_draws = []

    for raffle in raffles:
        first_image = raffle.media.filter(media_type='image').first()
        image_url = _safe_file_url(getattr(first_image, 'file', None)) or None

        total_numbers = RaffleNumber.objects.filter(
            raffle_list__raffle=raffle
        ).count()

        sold_numbers = RaffleNumber.objects.filter(
            raffle_list__raffle=raffle,
            is_sold=True
        ).count()

        revenue = sold_numbers * raffle.price_per_number

        percentage = 0
        if total_numbers > 0:
            percentage = (sold_numbers / total_numbers) * 100

        ready_for_draw = percentage >= raffle.min_sales_percentage
        can_manual_draw = raffle.is_active and ready_for_draw
        
        remaining_percentage = max(0, raffle.min_sales_percentage - percentage)

        item_data = {
            "raffle": raffle,
            "image_url": image_url,
            "total_numbers": total_numbers,
            "sold_numbers": sold_numbers,
            "revenue": revenue,
            "percentage": round(percentage, 2),
            "remaining_percentage": round(remaining_percentage, 2),
            "ready_for_draw": ready_for_draw,
            "can_manual_draw": can_manual_draw,
        }
        raffle_data.append(item_data)

        if can_manual_draw:
            eligible_for_draw.append(item_data)

        if raffle.is_active:
            in_filter_range = True
            filter_days = days_by_filter.get(draw_filter)
            if filter_days is not None:
                limit_date = now + timezone.timedelta(days=filter_days)
                in_filter_range = now <= raffle.draw_date <= limit_date

            if in_filter_range:
                upcoming_draws.append(item_data)

    upcoming_draws = sorted(upcoming_draws, key=lambda item: item['raffle'].draw_date)

    return render(request, "dashboard/home.html", {
        "raffle_data": raffle_data,
        "eligible_for_draw": eligible_for_draw,
        "upcoming_draws": upcoming_draws,
        "selected_draw_filter": draw_filter,
    })


@staff_member_required
def carousel_settings(request):
    edit_id = request.GET.get('edit')
    editing_slide = None
    if edit_id:
        editing_slide = get_object_or_404(HomeCarouselSlide, id=edit_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'create')

        if action == 'create':
            form = CarouselSlideForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Slide del carrusel creado correctamente.')
                return redirect('dashboard:carousel_settings')
            messages.error(request, 'Revisa el formulario para crear el slide.')

        elif action == 'update':
            slide_id = request.POST.get('slide_id')
            slide = get_object_or_404(HomeCarouselSlide, id=slide_id)
            form = CarouselSlideForm(request.POST, request.FILES, instance=slide)
            if form.is_valid():
                form.save()
                messages.success(request, 'Slide actualizado correctamente.')
                return redirect('dashboard:carousel_settings')
            editing_slide = slide
            messages.error(request, 'Revisa el formulario para actualizar el slide.')

        elif action == 'delete':
            slide_id = request.POST.get('slide_id')
            slide = get_object_or_404(HomeCarouselSlide, id=slide_id)
            slide.delete()
            messages.success(request, 'Slide eliminado correctamente.')
            return redirect('dashboard:carousel_settings')

        elif action == 'toggle':
            slide_id = request.POST.get('slide_id')
            slide = get_object_or_404(HomeCarouselSlide, id=slide_id)
            slide.is_active = not slide.is_active
            slide.save(update_fields=['is_active'])
            messages.success(request, 'Estado del slide actualizado.')
            return redirect('dashboard:carousel_settings')
    else:
        if editing_slide:
            form = CarouselSlideForm(instance=editing_slide)
        else:
            form = CarouselSlideForm(initial={'is_active': True, 'display_order': 0})

    slides = HomeCarouselSlide.objects.all().order_by('display_order', '-created_at')

    return render(request, 'dashboard/carousel_settings.html', {
        'form': form,
        'slides': slides,
        'editing_slide': editing_slide,
    })


@staff_member_required
def winner_profile_detail(request, user_id):
    winner_user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=winner_user)

    paid_purchases = list(
        Purchase.objects.filter(user=winner_user, status='paid')
        .select_related('raffle')
        .order_by('-created_at')
    )

    participation_by_raffle = {}
    raffle_ids = []

    for purchase in paid_purchases:
        raffle_id = purchase.raffle_id
        if raffle_id not in participation_by_raffle:
            participation_by_raffle[raffle_id] = {
                'raffle': purchase.raffle,
                'purchase_count': 0,
                'total_spent': 0,
                'last_purchase_at': purchase.created_at,
                'numbers': set(),
            }
            raffle_ids.append(raffle_id)

        entry = participation_by_raffle[raffle_id]
        entry['purchase_count'] += 1
        entry['total_spent'] += purchase.amount
        if purchase.created_at > entry['last_purchase_at']:
            entry['last_purchase_at'] = purchase.created_at

    if paid_purchases:
        numbers_rows = RaffleNumber.objects.filter(
            purchase__in=paid_purchases,
            is_sold=True,
        ).values('raffle_list__raffle_id', 'number')

        for row in numbers_rows:
            raffle_id = row['raffle_list__raffle_id']
            if raffle_id in participation_by_raffle:
                participation_by_raffle[raffle_id]['numbers'].add(row['number'])

    latest_draw_by_raffle = {}
    if raffle_ids:
        draws = Draw.objects.filter(raffle_id__in=raffle_ids).order_by('raffle_id', '-executed_at')
        for draw in draws:
            if draw.raffle_id not in latest_draw_by_raffle:
                latest_draw_by_raffle[draw.raffle_id] = draw

    participation_history = []
    for raffle_id, entry in participation_by_raffle.items():
        numbers_sorted = sorted(entry['numbers'])
        draw = latest_draw_by_raffle.get(raffle_id)

        if not draw:
            result_label = 'Pendiente'
            result_badge = 'bg-warning text-dark'
            winner_number = None
            is_winner = False
        else:
            winner_number = draw.winner_number
            is_winner = winner_number in entry['numbers']
            result_label = 'Ganador' if is_winner else 'No ganador'
            result_badge = 'bg-success' if is_winner else 'bg-secondary'

        participation_history.append({
            'raffle': entry['raffle'],
            'purchase_count': entry['purchase_count'],
            'total_spent': entry['total_spent'],
            'last_purchase_at': entry['last_purchase_at'],
            'numbers': numbers_sorted,
            'numbers_count': len(numbers_sorted),
            'winner_number': winner_number,
            'is_winner': is_winner,
            'result_label': result_label,
            'result_badge': result_badge,
        })

    participation_history.sort(key=lambda item: item['last_purchase_at'], reverse=True)

    return render(request, 'dashboard/winner_profile_detail.html', {
        'winner_user': winner_user,
        'winner_profile': profile,
        'participation_history': participation_history,
    })
