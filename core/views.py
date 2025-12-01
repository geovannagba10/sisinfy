from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth import logout, login, get_user_model
from django.contrib import messages
from .models import Item, Reserva, Exemplar
from .forms import ReservaForm, ReservaRetiradaForm, DevolucaoForm, PublicSignupForm, UsuarioTipoAcessoForm, UsuarioUpdateForm, RetiradaManualForm, NovoItemForm, NovoExemplarForm
from .decorators import gestao_required, diretoria_required
from django.views.decorators.http import require_GET

from django.http import JsonResponse
from django.db.models.functions import TruncDate, TruncMonth

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.text import slugify
from pathlib import Path
import json


User = get_user_model()


@login_required
def home(request):
    return render(request, 'core/home.html')



@login_required
def lista_itens(request):

    itens = (
        Item.objects
        .annotate(
            total_exemplares=Count('exemplares'),
            disponiveis=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.DISPONIVEL)
            ),
            reservados=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.RESERVADO)
            ),
            em_manutencao=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.EM_MANUTENCAO)
            ),
        )
        .order_by('nome')
    )

    try:
        logos_dir = Path(settings.BASE_DIR) / 'static' / 'core' / 'logos'
        available = {f.name for f in logos_dir.iterdir() if f.is_file()} if logos_dir.exists() else set()
    except Exception:
        available = set()

    exts = ['png', 'jpg', 'jpeg', 'svg', 'webp']

    itens_list = list(itens)
    for item in itens_list:
        item.logo_filename = None
        for ext in exts:
            candidate = f"{item.id}.{ext}"
            if candidate in available:
                item.logo_filename = candidate
                break
        if item.logo_filename:
            continue

        slug = slugify(item.nome or '')
        for ext in exts:
            candidate = f"{slug}.{ext}"
            if candidate in available:
                item.logo_filename = candidate
                break
        if item.logo_filename:
            continue

        if slug:
            for fname in available:
                if fname.startswith(slug):
                    item.logo_filename = fname
                    break

    return render(request, 'core/lista_itens.html', {'itens': itens_list})



@login_required
def reservar_item(request, item_id):

    item = get_object_or_404(Item, pk=item_id)

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.usuario = request.user
            reserva.item = item

            hoje = timezone.now().date()

            erros = False

            if reserva.data_retirada < hoje:
                form.add_error(
                    'data_retirada',
                    'A data de retirada não pode ser no passado.'
                )
                erros = True

            if reserva.data_devolucao < reserva.data_retirada:
                form.add_error(
                    'data_devolucao',
                    'A data de devolução não pode ser anterior à data de retirada.'
                )
                erros = True

            if (reserva.data_devolucao - reserva.data_retirada).days > 10:
                form.add_error(
                    'data_devolucao',
                    'A data de devolução deve estar no máximo 10 dias após a retirada.'
                )
                erros = True

            if not erros:
                reserva.status = Reserva.Status.PENDENTE
                reserva.save()
                return redirect('core:historico_reservas')
    else:
        form = ReservaForm()

    contexto = {
        'item': item,
        'form': form,
    }
    return render(request, 'core/reservar_item.html', contexto)


@login_required
def historico_reservas(request):

    reservas = (Reserva.objects
                .filter(usuario=request.user)
                .select_related('item')
                .order_by('-data_reserva'))
    return render(request, 'core/historico_reservas.html', {'reservas': reservas})


@login_required
def cancelar_reserva_usuario(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id, usuario=request.user)

    if request.method != 'POST':
        messages.warning(request, 'Ação inválida.')
        return redirect('core:historico_reservas')

    if reserva.status != Reserva.Status.PENDENTE:
        messages.warning(request, 'Só é possível cancelar reservas que ainda não foram confirmadas.')
        return redirect('core:historico_reservas')

    exemplar = reserva.exemplar
    if exemplar is not None and exemplar.situacao == Exemplar.Situacao.RESERVADO:
        exemplar.situacao = Exemplar.Situacao.DISPONIVEL
        exemplar.save()

    reserva.marcar_como_cancelada(motivo='Cancelada pelo usuário.', automatico=False, usuario=request.user)
    messages.success(request, 'Reserva cancelada com sucesso.')
    return redirect('core:historico_reservas')

def logout_view(request):

    logout(request)
    return redirect('login')


@login_required
@gestao_required
def reservas_pendentes(request):

    q = request.GET.get('q', '').strip()
    reservas = (Reserva.objects
                .filter(status=Reserva.Status.PENDENTE)
                .select_related('usuario', 'item'))

    if q:
        from django.db.models import Q
        filtros = (
            Q(usuario__nusp__icontains=q) |
            Q(usuario__username__icontains=q) |
            Q(usuario__email__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(item__codigo_tipo__icontains=q) |
            Q(item__nome__icontains=q)
        )
        if q.isdigit():
            filtros = filtros | Q(id=int(q))

        reservas = reservas.filter(filtros)

    reservas = reservas.order_by('-data_reserva')

    contexto = {
        'reservas': reservas,
        'q': q,
    }
    return render(request, 'core/reservas_pendentes.html', contexto)

@login_required
@gestao_required
def confirmar_retirada(request, reserva_id):

    reserva = get_object_or_404(Reserva, pk=reserva_id)

    if reserva.status != Reserva.Status.PENDENTE:
        return redirect('core:reservas_pendentes')

    if request.method == 'POST':
        form = ReservaRetiradaForm(request.POST, item=reserva.item)
        if form.is_valid():
            exemplar = form.cleaned_data['exemplar']

            reserva.exemplar = exemplar
            reserva.status = Reserva.Status.CONFIRMADO
            reserva.usuario_confirmou_retirada = request.user
            reserva.data_confirmou_retirada = timezone.now()
            reserva.save()

            exemplar.situacao = Exemplar.Situacao.RESERVADO
            exemplar.save()

            return redirect('core:reservas_ativas')
    else:
        form = ReservaRetiradaForm(item=reserva.item)

    return render(request, 'core/confirmar_retirada.html', {
        'reserva': reserva,
        'form': form,
    })



@login_required
@gestao_required
def cancelar_reserva(request, reserva_id):

    if request.method != 'POST':
        return redirect('core:reservas_pendentes')

    reserva = get_object_or_404(Reserva, pk=reserva_id)

    if reserva.status == Reserva.Status.PENDENTE:

        exemplar = reserva.exemplar
        if exemplar is not None and exemplar.situacao == Exemplar.Situacao.RESERVADO:
            exemplar.situacao = Exemplar.Situacao.DISPONIVEL
            exemplar.save()

        reserva.marcar_como_cancelada(
            motivo="Reserva cancelada pela gestão.",
            automatico=False,
            usuario=request.user
        )

    return redirect('core:reservas_pendentes')

@login_required
@gestao_required
def reservas_ativas(request):

    q = request.GET.get('q', '').strip()
    reservas = (Reserva.objects
                .filter(status=Reserva.Status.CONFIRMADO)
                .select_related('usuario', 'item'))

    if q:
        from django.db.models import Q
        filtros = (
            Q(usuario__nusp__icontains=q) |
            Q(usuario__username__icontains=q) |
            Q(usuario__email__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(item__codigo_tipo__icontains=q) |
            Q(item__nome__icontains=q)
        )
        if q.isdigit():
            filtros = filtros | Q(id=int(q))

        reservas = reservas.filter(filtros)

    reservas = reservas.order_by('-data_retirada')

    return render(request, 'core/reservas_ativas.html', {
        'reservas': reservas,
        'q': q,
    })


@login_required
@gestao_required
def confirmar_devolucao(request, reserva_id):

    reserva = get_object_or_404(Reserva, pk=reserva_id)

    if reserva.status != Reserva.Status.CONFIRMADO:
        return redirect('core:reservas_ativas')

    if request.method == 'POST':
        form = DevolucaoForm(request.POST)
        if form.is_valid():
            nova_condicao = form.cleaned_data['condicao']
            exemplar = reserva.exemplar

            if exemplar is not None:
                exemplar.condicao = nova_condicao

                if nova_condicao == Exemplar.Condicao.BOM:
                    exemplar.situacao = Exemplar.Situacao.DISPONIVEL
                else:
                    exemplar.situacao = Exemplar.Situacao.EM_MANUTENCAO

                exemplar.save()

            reserva.status = Reserva.Status.CONCLUIDA
            reserva.usuario_confirmou_devolucao = request.user
            reserva.data_confirmou_devolucao = timezone.now()
            reserva.save()

            return redirect('core:reservas_ativas')
    else:
        form = DevolucaoForm()

    return render(request, 'core/confirmar_devolucao.html', {
        'reserva': reserva,
        'form': form,
    })


def enviar_email_ativacao(user, request):
    """
    Envia um e-mail com link para ativar a conta do usuário.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    link_ativacao = request.build_absolute_uri(
        reverse('core:ativar_conta', args=[uid, token])
    )

    assunto = "Ative sua conta no TEM NO CAM"
    mensagem = (
        f"Olá, {user.get_full_name() or user.username}!\n\n"
        "Sua conta no TEM NO CAM foi criada, mas precisa ser ativada.\n"
        "Clique no link abaixo para ativar sua conta:\n\n"
        f"{link_ativacao}\n\n"
        "Se você não solicitou este cadastro, ignore este e-mail."
    )

    send_mail(
        assunto,
        mensagem,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )



def signup(request):
    """
    Cadastro público: cria um usuário sempre com tipo_acesso = 'Aluno'.
    Agora:
    - só permite e-mail @usp.br (validado no formulário)
    - cria o usuário inativo
    - envia e-mail com link para ativar a conta
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = PublicSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.tipo_acesso = 'Aluno'
            user.is_active = False
            user.save()

            enviar_email_ativacao(user, request)

            return render(request, 'registration/aguarde_ativacao.html', {
                'email': user.email,
            })
    else:
        form = PublicSignupForm()

    return render(request, 'registration/signup.html', {'form': form})

def ativar_conta(request, uidb64, token):
    """
    View acessada pelo link enviado por e-mail.
    Valida o token e ativa o usuário se tudo estiver ok.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        Usuario = get_user_model()
        user = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return render(request, 'registration/ativacao_sucesso.html', {'user': user})
    else:
        return render(request, 'registration/ativacao_invalida.html')



@login_required
@diretoria_required
def lista_usuarios(request):

    q = request.GET.get('q', '').strip()
    usuarios = User.objects.all()
    if q:
        from django.db.models import Q
        usuarios = usuarios.filter(
            Q(nusp__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    usuarios = usuarios.order_by('nusp')

    return render(request, 'core/lista_usuarios.html', {
        'usuarios': usuarios,
        'q': q,
    })


@login_required
@diretoria_required
def api_estatisticas(request):
    """
    API que retorna dados agregados de reservas em JSON.
    Será consumida pelo frontend Vue.
    """
    item_id = request.GET.get('item_id')

    reservas = Reserva.objects.all()
    if item_id:
        reservas = reservas.filter(item_id=item_id)

    # Reservas por dia
    reservas_por_dia_qs = (
        reservas
        .annotate(dia=TruncDate('data_reserva'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    reservas_por_dia = [
        {"dia": r["dia"].strftime("%Y-%m-%d"), "total": r["total"]}
        for r in reservas_por_dia_qs
    ]

    # Top 10 itens
    top_items_qs = (
        reservas
        .values('item__nome', 'item__codigo_tipo')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    top_items = [
        {
            "item": f"{r['item__codigo_tipo']} - {r['item__nome']}",
            "total": r["total"],
        }
        for r in top_items_qs
    ]

    # Reservas por mês
    reservas_mes_qs = (
        reservas
        .annotate(mes=TruncMonth('data_reserva'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    reservas_por_mes = [
        {"mes": r["mes"].strftime("%Y-%m"), "total": r["total"]}
        for r in reservas_mes_qs
    ]

    # Top usuários - forma alternativa
    top_usuarios_qs = (
        User.objects
        .annotate(total_reservas=Count('reservas'))
        .filter(total_reservas__gt=0)
        .order_by('-total_reservas')[:10]
    )
    top_usuarios = [
        {
            "nusp": u.nusp,
            "nome": u.get_full_name() or u.username or u.nusp,
            "total": u.total_reservas,
        }
        for u in top_usuarios_qs
    ]

    data = {
        "total_reservas": reservas.count(),
        "reservas_por_dia": reservas_por_dia,
        "top_itens": top_items,
        "reservas_por_mes": reservas_por_mes,
        "top_usuarios": top_usuarios,
    }
    return JsonResponse(data)

@login_required
@diretoria_required
def historico_reservas_completo(request):
    """
    Página para diretoria visualizar o histórico completo de todas as reservas
    com dados de confirmação (quem confirmou retirada/devolução e quando).
    """
    from django.core.paginator import Paginator
    
    status_filtro = request.GET.get('status', '')
    usuario_filtro = request.GET.get('usuario', '')
    item_filtro = request.GET.get('item', '')
    
    reservas = Reserva.objects.select_related(
        'usuario', 'item', 'exemplar',
        'usuario_confirmou_retirada',
        'usuario_confirmou_devolucao'
    ).order_by('-data_reserva')
    
    if status_filtro:
        reservas = reservas.filter(status=status_filtro)
    if usuario_filtro:
        reservas = reservas.filter(usuario__nusp__icontains=usuario_filtro)
    if item_filtro:
        reservas = reservas.filter(item__codigo_tipo__icontains=item_filtro)
    
    paginator = Paginator(reservas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    contexto = {
        'page_obj': page_obj,
        'reservas': page_obj.object_list,
        'status_choices': Reserva.Status.choices,
        'status_filtro': status_filtro,
        'usuario_filtro': usuario_filtro,
        'item_filtro': item_filtro,
        'total_reservas': reservas.count(),
    }
    return render(request, 'core/historico_reservas_completo.html', contexto)

@login_required
@diretoria_required
def estatisticas_vue(request):
    """
    Página de estatísticas: o HTML só carrega Vue + Chart.js.
    Os dados vêm da api_estatisticas em JSON.
    """
    itens = Item.objects.all().order_by('nome')

    itens_serializados = [
        {"id": i.id, "nome": i.nome, "codigo_tipo": i.codigo_tipo}
        for i in itens
    ]
    itens_json = json.dumps(itens_serializados, ensure_ascii=False)

    contexto = {
        "itens_json": itens_json,
    }
    return render(request, "core/estatisticas_vue.html", contexto)

@login_required
@diretoria_required
def alterar_tipo_acesso_usuario(request, usuario_id):

    usuario = get_object_or_404(User, pk=usuario_id)

    if request.method == 'POST':
        form = UsuarioTipoAcessoForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tipo de acesso de {usuario} atualizado com sucesso!')
            return redirect('core:lista_usuarios')
    else:
        form = UsuarioTipoAcessoForm(instance=usuario)

    contexto = {
        'usuario_alvo': usuario,
        'form': form,
    }
    return render(request, 'core/alterar_tipo_acesso_usuario.html', contexto)


@login_required
def editar_conta(request):
    """Permite que o usuário edite seu próprio nome, username e telefone.
    Mostra NUSP e e-mail como somente leitura no template.
    """
    from .forms import UsuarioUpdateForm

    usuario = request.user

    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados da conta atualizados com sucesso.')
            return redirect('core:editar_conta')
    else:
        form = UsuarioUpdateForm(instance=usuario)

    contexto = {
        'form': form,
        'nusp': usuario.nusp,
        'email': usuario.email,
    }
    return render(request, 'core/editar_conta.html', contexto)


@login_required
@gestao_required
def registrar_retirada_manual(request):
    """
    Página para GESTÃO/DIRETORIA registrar manualmente a retirada de um item para um aluno.
    """
    if request.method == 'POST':
        form = RetiradaManualForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data.get('usuario')
            reserva = form.save(commit=False)
            reserva.usuario = usuario
            reserva.status = Reserva.Status.CONFIRMADO
            reserva.save()
            messages.success(request, f'Retirada manual registrada com sucesso para {usuario.get_full_name()}.')
            return redirect('core:registrar_retirada_manual')
    else:
        form = RetiradaManualForm()

    contexto = {
        'form': form,
    }
    return render(request, 'core/registrar_retirada_manual.html', contexto)


@login_required
@diretoria_required
def modificar_estoque(request):
    """
    Página para DIRETORIA gerenciar estoque (itens e exemplares).
    Exibe todos os itens e permite criar novos tipos de itens.
    """
    itens = (
        Item.objects
        .annotate(
            total_exemplares=Count('exemplares'),
            disponiveis=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.DISPONIVEL)
            ),
            reservados=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.RESERVADO)
            ),
            em_manutencao=Count(
                'exemplares',
                filter=Q(exemplares__situacao=Exemplar.Situacao.EM_MANUTENCAO)
            ),
        )
        .order_by('nome')
    )

    if request.method == 'POST':
        form = NovoItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Novo tipo de item criado com sucesso.')
            return redirect('core:modificar_estoque')
    else:
        form = NovoItemForm()

    contexto = {
        'itens': itens,
        'form': form,
    }
    return render(request, 'core/modificar_estoque.html', contexto)


@login_required
@diretoria_required
def detalhe_item_estoque(request, item_id):
    """
    Página de detalhes de um item - exibe exemplares, permite criar/deletar exemplares.
    """
    item = get_object_or_404(Item, pk=item_id)
    exemplares = item.exemplares.all()

    if request.method == 'POST':
        if 'criar_exemplar' in request.POST:
            form = NovoExemplarForm(request.POST)
            if form.is_valid():
                exemplar = form.save(commit=False)
                exemplar.item = item
                exemplar.save()
                messages.success(request, 'Exemplar criado com sucesso.')
                return redirect('core:detalhe_item_estoque', item_id=item.id)
        elif 'deletar_exemplar' in request.POST:
            exemplar_id = request.POST.get('exemplar_id')
            exemplar = get_object_or_404(Exemplar, pk=exemplar_id, item=item)
            exemplar.delete()
            messages.success(request, 'Exemplar deletado com sucesso.')
            return redirect('core:detalhe_item_estoque', item_id=item.id)
    else:
        form = NovoExemplarForm()

    contexto = {
        'item': item,
        'exemplares': exemplares,
        'form': form,
    }
    return render(request, 'core/detalhe_item_estoque.html', contexto)

