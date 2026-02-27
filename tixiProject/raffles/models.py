from django.db import models
from django.utils import timezone

#Rifas
class Raffle(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price_per_number = models.DecimalField(max_digits=8, decimal_places=2)
    draw_date = models.DateTimeField()
    min_sales_percentage = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


#Media (images/videos for raffle)
class RaffleMedia(models.Model):
    MEDIA_TYPES = (
        ('image', 'Imagen'),
        ('video', 'Video'),
    )

    raffle = models.ForeignKey(
        Raffle,
        related_name='media',
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to='raffles/%Y/%m/%d/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.raffle.title} - {self.get_media_type_display()}"


class HomeCarouselSlide(models.Model):
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=180, blank=True)
    image = models.FileField(upload_to='branding/carousel/%Y/%m/%d/')
    link_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return f"Slide: {self.title}"

#Listas
class RaffleList(models.Model):
    raffle = models.ForeignKey(Raffle, related_name='lists', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_number = models.PositiveIntegerField()
    end_number = models.PositiveIntegerField()

#Numeros


class RaffleNumber(models.Model):
    raffle_list = models.ForeignKey(
        'RaffleList',
        related_name='numbers',
        on_delete=models.CASCADE
    )
    number = models.PositiveIntegerField()

    is_reserved = models.BooleanField(default=False)
    reserved_until = models.DateTimeField(null=True, blank=True)

    is_sold = models.BooleanField(default=False)

    purchase = models.ForeignKey(
        'payments.Purchase',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def reserve(self, purchase):
        self.is_reserved = True
        self.purchase = purchase
        self.reserved_until = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
