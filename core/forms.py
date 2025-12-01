from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Reserva, Exemplar, Item
from datetime import date
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model



class ReservaForm(forms.ModelForm):
    """
    Formulário que o ALUNO usa para fazer uma reserva.
    """
    class Meta:
        model = Reserva
        fields = ['data_retirada', 'data_devolucao']
        widgets = {
            'data_retirada': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_retirada = cleaned_data.get('data_retirada')
        data_devolucao = cleaned_data.get('data_devolucao')

        if data_retirada and data_devolucao:
            if data_devolucao < data_retirada:
                raise ValidationError("A data de devolução não pode ser anterior à data de retirada.")

            delta = (data_devolucao - data_retirada).days
            if delta > 10:
                raise ValidationError("O período máximo de empréstimo é de 10 dias a partir da retirada.")

        if data_retirada and data_retirada < date.today():
            raise ValidationError("A data de retirada não pode ser no passado.")

        return cleaned_data


class ReservaRetiradaForm(forms.ModelForm):
    """
    GESTÃO: escolher qual exemplar físico será entregue.
    """
    exemplar = forms.ModelChoiceField(
        queryset=Exemplar.objects.none(),
        required=True,
        label="Exemplar entregue"
    )

    class Meta:
        model = Reserva
        fields = ['exemplar']

    def __init__(self, *args, **kwargs):
        item = kwargs.pop('item')
        super().__init__(*args, **kwargs)
        self.fields['exemplar'].queryset = Exemplar.objects.filter(
            item=item,
            situacao=Exemplar.Situacao.DISPONIVEL,
            condicao=Exemplar.Condicao.BOM,
        )


class DevolucaoForm(forms.Form):
    """
    GESTÃO: registrar em que condição o exemplar voltou.
    """
    condicao = forms.ChoiceField(
        choices=Exemplar.Condicao.choices,
        label='Condição do exemplar após devolução'
    )

User = get_user_model()

class PublicSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            'nusp',
            'username',
            'first_name',
            'last_name',
            'email',
            'telefone',
        ]
        labels = {
            'nusp': 'NUSP',
            'username': 'Nome de usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
            'telefone': 'Telefone',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['password1'].label = 'Senha'
        self.fields['password1'].help_text = (
            "Sua senha deve ter pelo menos 8 caracteres e não pode ser muito "
            "parecida com seus dados pessoais."
        )

        self.fields['password2'].label = 'Confirmação de senha'
        self.fields['password2'].help_text = "Digite a mesma senha novamente para confirmação."

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email.endswith('@usp.br'):
            raise ValidationError('O e-mail deve ser um endereço @usp.br.')

        if User.objects.filter(email=email).exists():
            raise ValidationError('Já existe uma conta cadastrada com este e-mail.')

        return email

class UsuarioTipoAcessoForm(forms.ModelForm):
    """
    Form para a DIRETORIA alterar o tipo de acesso de um usuário.
    """
    class Meta:
        model = User
        fields = ['tipo_acesso']


class UsuarioUpdateForm(forms.ModelForm):
    """
    Form usado para que o usuário atualize seus próprios dados.
    Campos editáveis: `first_name`, `last_name`, `username`, `telefone`.
    Os campos `nusp` e `email` não são exibidos neste form (serão mostrados no template como leitura apenas).
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'telefone']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'username': 'Nome de usuário',
            'telefone': 'Telefone',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Já existe outro usuário com esse nome de usuário.')
        return username


class RetiradaManualForm(forms.ModelForm):
    """
    Form para GESTÃO/DIRETORIA registrar manualmente a retirada de um item para um aluno.
    Campos: identificador do aluno (NUSP ou email), item, data_retirada, data_devolucao.
    """
    usuario_identificador = forms.CharField(
        max_length=255,
        label='NUSP ou E-mail do aluno',
        help_text='Digite o NUSP ou e-mail do aluno'
    )

    class Meta:
        model = Reserva
        fields = ['usuario_identificador', 'item', 'data_retirada', 'data_devolucao']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'data_retirada': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'item': 'Item retirado',
            'data_retirada': 'Data de retirada',
            'data_devolucao': 'Data de devolução',
        }

    def clean(self):
        cleaned_data = super().clean()
        usuario_identificador = cleaned_data.get('usuario_identificador', '').strip()
        data_retirada = cleaned_data.get('data_retirada')
        data_devolucao = cleaned_data.get('data_devolucao')

        try:
            usuario = User.objects.get(
                Q(nusp=usuario_identificador) | Q(email=usuario_identificador)
            )
            cleaned_data['usuario'] = usuario
        except User.DoesNotExist:
            raise ValidationError('Usuário não encontrado. Verifique o NUSP ou e-mail.')

        if data_retirada and data_devolucao:
            if data_devolucao < data_retirada:
                raise ValidationError("A data de devolução não pode ser anterior à data de retirada.")

            delta = (data_devolucao - data_retirada).days
            if delta > 15:
                raise ValidationError("O período máximo de reserva é de 15 dias.")

        return cleaned_data


class NovoItemForm(forms.ModelForm):
    """
    Form para DIRETORIA criar um novo tipo de item.
    """
    class Meta:
        model = Item
        fields = ['nome', 'codigo_tipo', 'descricao', 'imagem']
        labels = {
            'nome': 'Nome do tipo de item',
            'codigo_tipo': 'Código do tipo',
            'descricao': 'Descrição',
            'imagem': 'Imagem do item',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'imagem': forms.FileInput(),
        }

    def clean_codigo_tipo(self):
        codigo_tipo = self.cleaned_data.get('codigo_tipo', '').strip().upper()
        qs = Item.objects.filter(codigo_tipo=codigo_tipo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um item com esse código de tipo.')
        return codigo_tipo


class NovoExemplarForm(forms.ModelForm):
    """
    Form para DIRETORIA criar um novo exemplar de um item.
    """
    class Meta:
        model = Exemplar
        fields = ['codigo_exemplar', 'situacao', 'condicao', 'observacoes']
        labels = {
            'codigo_exemplar': 'Código do exemplar',
            'situacao': 'Situação',
            'condicao': 'Condição',
            'observacoes': 'Observações',
        }
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_codigo_exemplar(self):
        codigo_exemplar = self.cleaned_data.get('codigo_exemplar', '').strip().upper()
        qs = Exemplar.objects.filter(codigo_exemplar=codigo_exemplar)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um exemplar com esse código.')
        return codigo_exemplar

