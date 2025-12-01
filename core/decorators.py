from django.http import HttpResponseForbidden
from functools import wraps


def gestao_required(view_func):
    """
    Permite acesso apenas para membros da gestao ou diretoria
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Você não está autenticado.')

        # Se o tipo_acesso for 'Aluno', bloqueia:
        if request.user.tipo_acesso == 'Aluno':
            return HttpResponseForbidden('Você não tem permissão para acessar esta página.')

        # Gestão / Diretoria passam
        return view_func(request, *args, **kwargs)

    return _wrapped_view

def diretoria_required(view_func):
    """
    Permite acesso apenas para usuários com tipo_acesso = 'Diretoria'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Você não está autenticado.')

        if request.user.tipo_acesso != 'Diretoria':
            return HttpResponseForbidden('Você não tem permissão para acessar esta página.')

        return view_func(request, *args, **kwargs)

    return _wrapped_view