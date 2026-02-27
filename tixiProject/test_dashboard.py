#!/usr/bin/env python
"""
Script para verificar que el dashboard es funcional.
Solo se ejecuta cuando se llama directamente.
"""
import os
from datetime import datetime, timedelta


def main():
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
    django.setup()

    from django.contrib.auth.models import User
    from django.test import Client
    from raffles.models import Raffle

    print("=" * 70)
    print("🔍 VERIFICACIÓN DE FUNCIONALIDAD DEL DASHBOARD")
    print("=" * 70)

    print("\n📝 1. Preparando usuario staff...")
    user, created = User.objects.get_or_create(
        username='testadmin',
        defaults={
            'email': 'testadmin@test.com',
            'is_staff': True,
            'is_superuser': False,
        },
    )
    user.set_password('testpass123')
    user.save()
    print(f"✅ Usuario staff 'testadmin' {'creado' if created else 'existente'}")

    print("\n📦 2. Preparando datos de test...")
    raffle, created = Raffle.objects.get_or_create(
        title='Test Raffle Dashboard',
        defaults={
            'description': 'Rifa para testing del dashboard',
            'price_per_number': 2.00,
            'draw_date': datetime.now() + timedelta(days=7),
            'min_sales_percentage': 50,
            'is_active': True,
        },
    )
    print(f"✅ Rifa 'Test Raffle Dashboard' {'creada' if created else 'existente'}")

    print("\n🧪 3. Testando acceso a vistas del dashboard...")
    client = Client()
    login_ok = client.login(username='testadmin', password='testpass123')
    print(f"✅ Login: {'Exitoso' if login_ok else 'Fallido'}")

    test_urls = {
        '/dashboard/': 'Dashboard Home',
        '/dashboard/raffles/create/': 'Crear Rifa',
        f'/dashboard/raffle/{raffle.id}/': 'Detalle de Rifa',
        f'/dashboard/raffle/{raffle.id}/add_list/': 'Agregar Lista',
        '/dashboard/draws/': 'Historial de Sorteos',
    }

    print("\n📍 Probando URLs del dashboard:")
    all_ok = True
    for url, name in test_urls.items():
        response = client.get(url)
        status = "✅" if response.status_code == 200 else f"⚠️  ({response.status_code})"
        print(f"   {status} {name:30} → {url}")
        all_ok = all_ok and response.status_code == 200

    print("\n" + "=" * 70)
    if all_ok:
        print("✅ DASHBOARD COMPLETAMENTE FUNCIONAL")
    else:
        print("⚠️ DASHBOARD CON ADVERTENCIAS")
    print("=" * 70)


if __name__ == '__main__':
    main()
