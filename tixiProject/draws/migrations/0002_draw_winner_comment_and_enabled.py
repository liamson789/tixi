from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('draws', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='draw',
            name='winner_comment',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='draw',
            name='winner_comment_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
