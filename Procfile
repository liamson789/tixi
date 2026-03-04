release: cd tixiProject && python manage.py migrate --noinput
web: cd tixiProject && gunicorn tixiProject.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
