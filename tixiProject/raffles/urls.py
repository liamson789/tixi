from django.urls import path
from . import api
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('ganadores/', views.winners, name='winners'),
    path('<int:raffle_id>/winner-comment/', views.submit_winner_comment, name='submit_winner_comment'),
    path('api/lists/<int:list_id>/available/', api.AvailableNumbersAPIView.as_view(), name='api-available-numbers'),
    path('api/reserve/', api.ReserveNumbersAPIView.as_view(), name='api-reserve-numbers'),
    path('<int:raffle_id>/', views.raffle_detail, name='raffle_detail'),
    path('<int:raffle_id>/status/', views.raffle_status, name='raffle_status'),
]
