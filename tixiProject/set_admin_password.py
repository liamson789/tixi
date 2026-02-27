#!/usr/bin/env python
"""
Script para establecer contraseña del admin
"""
import os
import django
import secrets
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 70)
print("🔐 ESTABLECER CONTRASEÑA DEL ADMIN")
print("=" * 70)

# Generar contraseña segura
password_chars = string.ascii_letters + string.digits + "!@#$%&*"
secure_password = ''.join(secrets.choice(password_chars) for _ in range(16))

try:
    user = User.objects.get(username='admin')
    user.set_password(secure_password)
    user.save()
    
    print("\n" + "=" * 70)
    print("✅ CONTRASEÑA ESTABLECIDA EXITOSAMENTE")
    print("=" * 70)
    print(f"""
📋 Credenciales para Acceso Admin:
   • Usuario: admin
   • Email: {user.email}
   • Contraseña: {secure_password}

🌐 Para acceder:
   1. URL: http://localhost:8000/admin/
   2. Usuario: admin
   3. Contraseña: {secure_password}

📌 Copia y guarda esta contraseña en un lugar seguro.

También puedes cambiar la contraseña ejecutando:
   python manage.py changepassword admin
    """)
    print("=" * 70)
    
except User.DoesNotExist:
    print("\n❌ El usuario admin no existe. Ejecuta create_admin.py primero")
    exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
