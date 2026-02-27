from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raffles', '0003_rafflemedia_remove_rafflelistmedia'),
    ]

    operations = [
        migrations.CreateModel(
            name='HomeCarouselSlide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('subtitle', models.CharField(blank=True, max_length=180)),
                ('image', models.FileField(upload_to='branding/carousel/%Y/%m/%d/')),
                ('link_url', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['display_order', '-created_at'],
            },
        ),
    ]
