from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from . import views 
from .views import (
    dashboard_home,
    create_raffle,
    edit_raffle,
    delete_raffle,
    raffle_detail,
    add_list,
    edit_list,
    delete_list,
    delete_raffle_media,
    manual_draw,
    draw_history,
    winner_profile_detail,
    carousel_settings,
)

app_name = 'dashboard'

urlpatterns = [
    # Home
    path('', staff_member_required(dashboard_home), name='home'),
    
    # Rafles CRUD
    path('raffles/create/', staff_member_required(create_raffle), name='raffle_create'),
    path('raffle/<int:raffle_id>/', staff_member_required(raffle_detail), name='raffle_detail'),
    path('raffle/<int:raffle_id>/edit/', staff_member_required(edit_raffle), name='raffle_edit'),
    path('raffle/<int:raffle_id>/delete/', staff_member_required(delete_raffle), name='raffle_delete'),
    
    # Listas CRUD
    path('raffle/<int:raffle_id>/add_list/', staff_member_required(add_list), name='add_list'),
    path('list/<int:list_id>/edit/', staff_member_required(edit_list), name='list_edit'),
    path('list/<int:list_id>/delete/', staff_member_required(delete_list), name='list_delete'),
    
    # Medios
    path('media/<int:media_id>/delete/', staff_member_required(delete_raffle_media), name='media_delete'),
    
    # Sorteos
    path('raffle/<int:raffle_id>/manual_draw/', staff_member_required(manual_draw), name='manual_draw'),
    path('raffle/<int:raffle_id>/winner-comment/toggle/', staff_member_required(views.toggle_winner_comment), name='toggle_winner_comment'),
    path('draws/', staff_member_required(draw_history), name='draw_history'),
    path('winner/<int:user_id>/profile/', staff_member_required(winner_profile_detail), name='winner_profile_detail'),

    # Configuración
    path('settings/carousel/', staff_member_required(carousel_settings), name='carousel_settings'),
]
