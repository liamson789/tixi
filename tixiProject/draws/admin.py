from django.contrib import admin
from .models import Draw

# Register your models here.


@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'raffle',
		'winner_number',
		'winner_comment_enabled',
		'executed_at',
	)
	list_filter = ('winner_comment_enabled', 'executed_at')
	search_fields = ('raffle__title', 'winner_comment')
	list_editable = ('winner_comment_enabled',)
