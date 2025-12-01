from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Item, Exemplar, Reserva


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # qual campo é usado como username
    model = Usuario
    list_display = ('nusp', 'username', 'email', 'tipo_acesso', 'is_staff', 'is_superuser')
    search_fields = ('nusp', 'username', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('Informações extras', {'fields': ('nusp', 'tipo_acesso','telefone')}),
    )

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('codigo_tipo', 'nome')
    search_fields = ('codigo_tipo', 'nome')

@admin.register(Exemplar)
class ExemplarAdmin(admin.ModelAdmin):
    list_display = ('codigo_exemplar', 'item', 'situacao', 'condicao')
    list_filter = ('situacao', 'condicao', 'item')
    search_fields = ('codigo_exemplar', 'item__nome', 'item__codigo_tipo')

    
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario',
        'usuario_cancelou',
        'item',
        'exemplar',
        'status',
        'data_reserva',
        'data_retirada',
        'data_devolucao',
        'usuario_confirmou_retirada',
        'data_confirmou_retirada',
        'usuario_confirmou_devolucao',
        'data_confirmou_devolucao',
        'cancelada_em',
        'cancelamento_automatico',
    )
    list_filter = (
        'status',
        'cancelamento_automatico',
        'data_retirada',
        'data_devolucao',
    )
    search_fields = ('usuario__nusp', 'item__codigo_tipo')
    readonly_fields = (
        'data_reserva',
        'usuario_confirmou_retirada',
        'data_confirmou_retirada',
        'usuario_confirmou_devolucao',
        'data_confirmou_devolucao',
        'cancelada_em',
        'usuario_cancelou',
    )
    fieldsets = (
        ('Informações da Reserva', {
            'fields': ('usuario', 'item', 'exemplar', 'status', 'data_reserva')
        }),
        ('Datas da Reserva', {
            'fields': ('data_retirada', 'data_devolucao')
        }),
        ('Confirmação de Retirada', {
            'fields': ('usuario_confirmou_retirada', 'data_confirmou_retirada')
        }),
        ('Confirmação de Devolução', {
            'fields': ('usuario_confirmou_devolucao', 'data_confirmou_devolucao')
        }),
        ('Cancelamento', {
            'fields': ('cancelada_em', 'usuario_cancelou', 'motivo_cancelamento', 'cancelamento_automatico')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
    )





