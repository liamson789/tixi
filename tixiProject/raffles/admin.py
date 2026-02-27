from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import Raffle, RaffleList, RaffleNumber, RaffleMedia, HomeCarouselSlide

class RaffleMediaInline(admin.TabularInline):
    model = RaffleMedia
    extra = 1
    readonly_fields = ('uploaded_at',)
    fields = ('file', 'media_type', 'uploaded_at')

class RaffleNumberInline(admin.TabularInline):
    model = RaffleNumber
    extra = 0
    fields = ('number', 'is_sold', 'is_reserved', 'purchase')
    readonly_fields = ('number',)
    can_delete = False

class RaffleListInline(admin.StackedInline):
    model = RaffleList
    extra = 1
    fields = ('name', 'start_number', 'end_number')

@admin.register(Raffle)
class RaffleAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'price_per_number', 'draw_date', 'stats_display', 'status_display', 'created_at')
    list_filter = ('is_active', 'created_at', 'draw_date', 'min_sales_percentage')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'stats_details')
    fieldsets = (
        ('Información General', {
            'fields': ('title', 'description')
        }),
        ('Configuración de Precios', {
            'fields': ('price_per_number', 'min_sales_percentage')
        }),
        ('Sorteo', {
            'fields': ('draw_date', 'is_active')
        }),
        ('Estadísticas', {
            'fields': ('stats_details', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [RaffleMediaInline, RaffleListInline]
    actions = ['enable_raffles', 'disable_raffles']

    def title_display(self, obj):
        return f"🎰 {obj.title}"
    title_display.short_description = "Título"

    def status_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✅ Activa</span>')
        return format_html('<span style="color: red;">❌ Inactiva</span>')
    status_display.short_description = "Estado"

    def stats_display(self, obj):
        total = obj.lists.aggregate(
            total=Count('numbers')
        )['total'] or 0
        sold = RaffleNumber.objects.filter(
            raffle_list__raffle=obj,
            is_sold=True
        ).count()
        
        if total > 0:
            percentage = (sold / total) * 100
            return f"📊 {sold}/{total} ({percentage:.0f}%)"
        return "Sin números"
    stats_display.short_description = "Ventas"

    def stats_details(self, obj):
        total = RaffleNumber.objects.filter(
            raffle_list__raffle=obj
        ).count()
        sold = RaffleNumber.objects.filter(
            raffle_list__raffle=obj,
            is_sold=True
        ).count()
        reserved = RaffleNumber.objects.filter(
            raffle_list__raffle=obj,
            is_reserved=True
        ).count()
        
        if total > 0:
            percentage = (sold / total) * 100
        else:
            percentage = 0
            
        return f"""
        <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
            <p><strong>Total de números:</strong> {total}</p>
            <p><strong>Vendidos:</strong> {sold}</p>
            <p><strong>Reservados:</strong> {reserved}</p>
            <p><strong>Disponibles:</strong> {total - sold - reserved}</p>
            <div style="background: #ddd; height: 20px; border-radius: 3px; overflow: hidden; margin: 10px 0;">
                <div style="background: {self._get_color(percentage)}; height: 100%; width: {min(percentage, 100)}%;"></div>
            </div>
            <p><strong>Progreso:</strong> {percentage:.2f}%</p>
        </div>
        """
    stats_details.allow_tags = True

    def _get_color(self, percentage):
        if percentage >= 80:
            return "#28a745"
        elif percentage >= 50:
            return "#ffc107"
        else:
            return "#dc3545"

    def enable_raffles(self, request, queryset):
        queryset.update(is_active=True)
    enable_raffles.short_description = "✅ Activar rifas seleccionadas"

    def disable_raffles(self, request, queryset):
        queryset.update(is_active=False)
    disable_raffles.short_description = "❌ Desactivar rifas seleccionadas"

@admin.register(RaffleList)
class RaffleListAdmin(admin.ModelAdmin):
    list_display = ('name', 'raffle', 'range_display', 'count_display', 'sales_display')
    list_filter = ('raffle', 'raffle__is_active')
    search_fields = ('name', 'raffle__title')
    readonly_fields = ('created_at', 'stats_details') if hasattr(RaffleList, 'created_at') else ('stats_details',)
    fieldsets = (
        ('Información', {
            'fields': ('raffle', 'name', 'start_number', 'end_number')
        }),
        ('Estadísticas', {
            'fields': ('stats_details',),
            'classes': ('collapse',)
        }),
    )
    inlines = [RaffleNumberInline]
    actions = ['view_numbers']

    def range_display(self, obj):
        return f"{obj.start_number} - {obj.end_number}"
    range_display.short_description = "Rango"

    def count_display(self, obj):
        count = obj.numbers.count()
        return f"📊 {count} números"
    count_display.short_description = "Total"

    def sales_display(self, obj):
        total = obj.numbers.count()
        sold = obj.numbers.filter(is_sold=True).count()
        if total > 0:
            percentage = (sold / total) * 100
            return f"✅ {sold}/{total} ({percentage:.0f}%)"
        return "0/0"
    sales_display.short_description = "Vendidos"

    def stats_details(self, obj):
        total = obj.numbers.count()
        sold = obj.numbers.filter(is_sold=True).count()
        reserved = obj.numbers.filter(is_reserved=True).count()
        available = total - sold - reserved
        
        if total > 0:
            percentage = (sold / total) * 100
        else:
            percentage = 0
            
        return f"""
        <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
            <p><strong>Total:</strong> {total}</p>
            <p><strong>Vendidos:</strong> {sold}</p>
            <p><strong>Disponibles:</strong> {available}</p>
            <div style="background: #ddd; height: 20px; border-radius: 3px; overflow: hidden; margin: 10px 0;">
                <div style="background: #28a745; height: 100%; width: {min(percentage, 100)}%;"></div>
            </div>
            <p><strong>Progreso:</strong> {percentage:.2f}%</p>
        </div>
        """
    stats_details.allow_tags = True

    def view_numbers(self, request, queryset):
        pass
    view_numbers.short_description = "Ver números"

@admin.register(RaffleNumber)
class RaffleNumberAdmin(admin.ModelAdmin):
    list_display = ('number_display', 'raffle_list', 'status_display', 'purchase_link')
    list_filter = ('is_sold', 'is_reserved', 'raffle_list__raffle', 'raffle_list')
    search_fields = ('number', 'raffle_list__name', 'raffle_list__raffle__title')
    readonly_fields = ('raffle_list', 'number')
    fieldsets = (
        ('Información', {
            'fields': ('raffle_list', 'number')
        }),
        ('Estado', {
            'fields': ('is_sold', 'is_reserved', 'reserved_until', 'purchase')
        }),
    )
    actions = ['mark_as_sold', 'mark_as_available']

    def number_display(self, obj):
        return f"🔢 {obj.number}"
    number_display.short_description = "Número"

    def status_display(self, obj):
        if obj.is_sold:
            return format_html('<span style="color: green; font-weight: bold;">✅ VENDIDO</span>')
        elif obj.is_reserved:
            return format_html('<span style="color: orange; font-weight: bold;">⏳ RESERVADO</span>')
        return format_html('<span style="color: blue;">📌 DISPONIBLE</span>')
    status_display.short_description = "Estado"

    def purchase_link(self, obj):
        if obj.purchase:
            url = reverse('admin:payments_purchase_change', args=(obj.purchase.id,))
            return format_html('<a href="{}">{}</a>', url, obj.purchase)
        return "-"
    purchase_link.short_description = "Compra"

    def mark_as_sold(self, request, queryset):
        queryset.update(is_sold=True, is_reserved=False)
    mark_as_sold.short_description = "✅ Marcar como vendido"

    def mark_as_available(self, request, queryset):
        queryset.update(is_sold=False, is_reserved=False)
    mark_as_available.short_description = "📌 Marcar como disponible"

@admin.register(RaffleMedia)
class RaffleMediaAdmin(admin.ModelAdmin):
    list_display = ('raffle', 'media_display', 'file_size', 'uploaded_at')
    list_filter = ('media_type', 'uploaded_at', 'raffle')
    search_fields = ('raffle__title', 'file')
    readonly_fields = ('uploaded_at', 'preview_display')
    fieldsets = (
        ('Informacion', {
            'fields': ('raffle', 'file', 'media_type')
        }),
        ('Vista Previa', {
            'fields': ('preview_display',),
            'classes': ('collapse',)
        }),
        ('Detalles', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )

    def media_display(self, obj):
        icons = {'image': '🖼️', 'video': '🎥'}
        return f"{icons.get(obj.media_type, '📁')} {obj.get_media_type_display()}"
    media_display.short_description = "Tipo"

    def file_size(self, obj):
        try:
            size_bytes = obj.file.size
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "-"
    file_size.short_description = "Tamaño"

    def preview_display(self, obj):
        if obj.media_type == 'image':
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px;">',
                obj.file.url
            )
        return f'<a href="{obj.file.url}" target="_blank">Ver archivo</a>'
    preview_display.allow_tags = True
    preview_display.short_description = "Vista Previa"


@admin.register(HomeCarouselSlide)
class HomeCarouselSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle', 'link_url')
    readonly_fields = ('created_at', 'preview_display')
    fieldsets = (
        ('Contenido', {
            'fields': ('title', 'subtitle', 'image', 'link_url')
        }),
        ('Visualización', {
            'fields': ('display_order', 'is_active')
        }),
        ('Vista previa', {
            'fields': ('preview_display',),
            'classes': ('collapse',)
        }),
        ('Detalles', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    ordering = ('display_order', '-created_at')

    def preview_display(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 460px; max-height: 220px; border-radius: 8px;">',
                obj.image.url
            )
        return "Sin imagen"

    preview_display.short_description = "Preview"
