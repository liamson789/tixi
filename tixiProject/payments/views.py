from django.shortcuts import render
import uuid
from django.conf import settings
from django.http import JsonResponse
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Purchase


@login_required
@require_POST
def create_checkout(request):
    """
    Crea un nuevo checkout de Wompi.
    
    POST params:
    - raffle_id: ID de la rifa
    - amount: Monto a pagar (en dólares)
    
    Returns:
    - checkout_url: URL para redirigir al cliente a Wompi
    """
    user = request.user
    raffle_id = request.POST.get('raffle_id')
    amount = request.POST.get('amount')
    
    if not raffle_id or not amount:
        return JsonResponse({'error': 'Missing raffle_id or amount'}, status=400)

    try:
        normalized_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    if normalized_amount <= 0:
        return JsonResponse({'error': 'Amount must be greater than zero'}, status=400)

    reference = f"TIXI-{uuid.uuid4()}"

    purchase = Purchase.objects.create(
        user=user,
        raffle_id=raffle_id,
        amount=normalized_amount,
        reference=reference
    )

    base_url = getattr(settings, 'APP_BASE_URL', '') or getattr(settings, 'NGROK_URL', '')
    if not base_url:
        purchase.status = 'failed'
        purchase.save(update_fields=['status'])
        return JsonResponse({'error': 'APP_BASE_URL is not configured'}, status=500)

    redirect_params = urlencode({
        'reference': reference,
        'raffle_id': raffle_id,
    })

    checkout_url = (
        "https://checkout.wompi.sv/p/"
        f"{settings.WOMPI_PUBLIC_KEY}"
        f"?reference={reference}"
        f"&amount-in-cents={int(normalized_amount * 100)}"
        f"&currency=USD"
        f"&redirect-url={base_url}/payment/return?{redirect_params}"
    )

    return JsonResponse({"checkout_url": checkout_url})


def payment_return(request):
    reference = request.GET.get('reference') or request.GET.get('Referencia')
    wompi_status = (
        request.GET.get('status')
        or request.GET.get('ResultadoTransaccion')
        or request.GET.get('resultado')
    )

    raffle_id = request.GET.get('raffle_id')
    purchase = Purchase.objects.filter(reference=reference).first() if reference else None

    if not raffle_id and purchase:
        raffle_id = purchase.raffle_id

    context = {
        'reference': reference,
        'wompi_status': wompi_status,
        'purchase': purchase,
        'raffle_id': raffle_id,
    }
    return render(request, 'payments/payment_return.html', context)


def payment_status(request):
    reference = request.GET.get('reference')
    if not reference:
        return JsonResponse({'detail': 'Missing reference'}, status=400)

    purchase = Purchase.objects.filter(reference=reference).first()
    if not purchase:
        return JsonResponse({'detail': 'Purchase not found'}, status=404)

    return JsonResponse({
        'reference': purchase.reference,
        'status': purchase.status,
        'amount': float(purchase.amount),
    })

