from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):

    nusp = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='NUSP'
    )

    class TiposAcesso(models.TextChoices):
        ALUNO = 'Aluno', 'Aluno'
        MEMBRO_GESTAO = 'MembroGestao', 'Membro da Gestão'
        DIRETORIA = 'Diretoria', 'Diretoria de Patrimônio'

    tipo_acesso = models.CharField(
        max_length=20,
        choices=TiposAcesso.choices,
        default=TiposAcesso.ALUNO,
        verbose_name='Tipo de acesso'
    )
    
    telefone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefone'
    )


    # Vamos usar o NUSP como "username" para login
    USERNAME_FIELD = 'nusp'
    REQUIRED_FIELDS = ['username', 'email']  # o que o createsuperuser ainda exige

    def __str__(self):
        # Isso define como o usuário aparece no admin, etc.
        return f'{self.nusp} - {self.get_full_name() or self.username}'

class Item(models.Model):

    # Nome do tipo do item (ex.: "Calculadora Científica", "Jaleco", etc.)
    nome = models.CharField(
        max_length=255,
        verbose_name='Nome do tipo de item'
    )

    # Código do TIPO, não do exemplar físico.
    # Ex.: "JAL-M", "OC-01", "CALC-CIENT"
    codigo_tipo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código do tipo',
    )

    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição',
        help_text='Detalhes do item (tamanho, uso, observações gerais).'
    )

    # Campo de imagem — adicionamos aqui
    imagem = models.ImageField(
        upload_to='itens/',    # pasta dentro de MEDIA_ROOT
        blank=True,
        null=True,
        verbose_name='Imagem do item'
    )

    def __str__(self):
        return f'{self.codigo_tipo} - {self.nome}'
    
    
class Exemplar(models.Model):
    class Situacao(models.TextChoices):
        DISPONIVEL = 'Disponivel', 'Disponível'
        RESERVADO = 'Reservado', 'Reservado'
        EM_MANUTENCAO = 'Em manutencao', 'Em manutenção'

    class Condicao(models.TextChoices):
        BOM = 'Bom', 'Bom'
        DEFEITUOSO = 'Defeituoso', 'Defeituoso'

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='exemplares',
        verbose_name='Tipo de item',
    )

    codigo_exemplar = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Código do exemplar',
    )

    situacao = models.CharField(
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.DISPONIVEL,
        verbose_name='Situação',
    )

    condicao = models.CharField(
        max_length=20,
        choices=Condicao.choices,
        default=Condicao.BOM,
        verbose_name='Condição',
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
    )

    def __str__(self):
        return f'{self.codigo_exemplar} ({self.item.nome}) - {self.situacao} / {self.condicao}'

class Reserva(models.Model):

    class Status(models.TextChoices):
        PENDENTE = 'Pendente', 'Pendente'          # aluno reservou, gestão ainda não confirmou
        CONFIRMADO = 'Confirmado', 'Confirmado'    # retirada feita / empréstimo ativo
        CANCELADA = 'Cancelada', 'Cancelada'       # cancelada antes da retirada (manual ou automática)
        CONCLUIDA = 'Concluida', 'Concluída'       # devolução registrada

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Usuário'
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Tipo de item'
    )
    
    exemplar = models.ForeignKey(
        Exemplar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas'
    )

    data_reserva = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data da reserva'
    )

    # continua sendo só a DATA escolhida para buscar
    data_retirada = models.DateField(
        verbose_name='Data prevista para retirada'
    )

    data_devolucao = models.DateField(
        verbose_name='Data prevista para devolução'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name='Status'
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Comentários sobre esta reserva (motivo, situação específica etc.).'
    )

    # === NOVOS CAMPOS PARA CONTROLAR CANCELAMENTO ===
    cancelada_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data/hora do cancelamento'
    )

    motivo_cancelamento = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Motivo do cancelamento',
        help_text='Ex.: cancelada pelo aluno, não retirada em 24h, item indisponível, etc.'
    )

    cancelamento_automatico = models.BooleanField(
        default=False,
        verbose_name='Cancelamento automático'
    )
    # ================================================

    usuario_cancelou = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_canceladas',
        verbose_name='Quem cancelou'
    )

    # === CAMPOS PARA RASTREAR CONFIRMAÇÕES ===
    usuario_confirmou_retirada = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_confirmadas_retirada',
        verbose_name='Quem confirmou a retirada'
    )

    data_confirmou_retirada = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data/hora que confirmou a retirada'
    )

    usuario_confirmou_devolucao = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_confirmadas_devolucao',
        verbose_name='Quem confirmou a devolução'
    )

    data_confirmou_devolucao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data/hora que confirmou a devolução'
    )
    # ================================================

    def __str__(self):
        return f'Reserva #{self.id} - {self.usuario.nusp} - {self.item.codigo_tipo} ({self.status})'

    # helper pra não repetir lógica na view / job
    def marcar_como_cancelada(self, motivo: str = '', automatico: bool = False, usuario=None):
        """
        Marca a reserva como cancelada, atualizando campos relacionados e salvando no banco.
        Vai ser usada tanto no cancelamento manual quanto no automático.
        """
        # se já não estiver pendente/confirmada, não faz nada
        if self.status == self.Status.CANCELADA or self.status == self.Status.CONCLUIDA:
            return

        self.status = self.Status.CANCELADA
        self.cancelada_em = timezone.now()
        self.motivo_cancelamento = motivo or self.motivo_cancelamento
        self.cancelamento_automatico = automatico
        # registrar quem realizou o cancelamento quando fornecido
        if usuario is not None:
            try:
                self.usuario_cancelou = usuario
            except Exception:
                # se algo inesperado ocorrer, não bloquear o cancelamento
                pass
        self.save()
        
# Deixar comentado ou remover ReservaHistorico se não precisar mais
class ReservaHistorico(models.Model):
    """
    DESCONTINUADO: Os dados foram consolidados no modelo Reserva.
    Essa classe pode ser removida após criar uma migration de limpeza.
    """
    pass

