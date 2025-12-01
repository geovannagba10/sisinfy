from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('itens/', views.lista_itens, name='lista_itens'),
    path('itens/<int:item_id>/reservar/', views.reservar_item, name='reservar_item'),
    path('reservas/', views.historico_reservas, name='historico_reservas'),
    path('reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva_usuario, name='cancelar_reserva_usuario'),

    path('gestao/reservas/pendentes/', views.reservas_pendentes, name='reservas_pendentes'),
    path('gestao/reservas/ativas/', views.reservas_ativas, name='reservas_ativas'),
    path('gestao/reservas/<int:reserva_id>/confirmar-retirada/', views.confirmar_retirada, name='confirmar_retirada'),
    path('gestao/reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    path('gestao/reservas/<int:reserva_id>/confirmar-devolucao/', views.confirmar_devolucao, name='confirmar_devolucao'),
    path('gestao/registrar-retirada-manual/', views.registrar_retirada_manual, name='registrar_retirada_manual'),

    path('gestao/usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('gestao/usuarios/<int:usuario_id>/alterar-acesso/', views.alterar_tipo_acesso_usuario, name='alterar_tipo_acesso_usuario'),
    path('gestao/modificar-estoque/', views.modificar_estoque, name='modificar_estoque'),
    path('gestao/estoque/item/<int:item_id>/', views.detalhe_item_estoque, name='detalhe_item_estoque'),
    path("estatisticas/", views.estatisticas_vue, name="estatisticas"),
    path("estatisticas/api/", views.api_estatisticas, name="api_estatisticas"),
    path('conta/editar/', views.editar_conta, name='editar_conta'),
    path('gestao/reservas/historico-completo/', views.historico_reservas_completo, name='historico_reservas_completo'),
    
    path('ativar-conta/<slug:uidb64>/<slug:token>/', views.ativar_conta, name='ativar_conta'),


]

