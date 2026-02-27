#!/usr/bin/env python
"""
Script para crear usuario admin/superuser
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tixiProject.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 70)
print("👤 CREADOR DE USUARIO ADMIN")
print("=" * 70)

# Credenciales predefinidas
username = "admin"
email = "admin@tixipwa.com"
password = "Admin123456!"

# Validar que el usuario no exista
if User.objects.filter(username=username).exists():
    print(f"\n⚠️  El usuario '{username}' ya existe")
    print(f"\nPara cambiar la contraseña:")
    print(f"   python manage.py changepassword {username}")
    exit(0)

try:
    # Crear usuario superuser
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    
    print("\n" + "=" * 70)
    print("✅ USUARIO ADMIN CREADO EXITOSAMENTE")
    print("=" * 70)
    print(f"""
📋 Credenciales de Acceso:
   • Usuario: {username}
   • Email: {email}
   • Contraseña: {password}

🌐 Para acceder al admin:
   1. Abre: http://localhost:8000/admin/
   2. Ingresa:
      - Usuario: {username}
      - Contraseña: {password}

📊 Podrás administrar:
   ✓ Rifas (crear, editar, eliminar)
   ✓ Usuarios
   ✓ Pagos
   ✓ Registros de Webhooks
   ✓ Sorteos

⚠️  NOTAS IMPORTANTES:
   • Cambiar la contraseña después de primera vez
   • Usar credenciales seguras en producción
   • Comando para cambiar contraseña:
     python manage.py changepassword {username}
    """)
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error al crear usuario: {e}")
    exit(1)

