from django.urls import path
from . import api

urlpatterns = [
    path('api/lists/<int:list_id>/available/', api.AvailableNumbersAPIView.as_view(), name='api-available-numbers'),
    path('api/reserve/', api.ReserveNumbersAPIView.as_view(), name='api-reserve-numbers'),
]
