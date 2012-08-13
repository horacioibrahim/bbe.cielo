# -*- coding: utf-8 -*-
import inspect
import datetime
import colander
from decimal import Decimal


SERVICE_VERSION = '1.1.1'


LANG_PT = 'PT'
LANG_EN = 'EN'
LANG_ES = 'ES'

LANGUAGES = (LANG_PT, LANG_EN, LANG_ES)


MASTERCARD = 'mastercard'
DINERS = 'diners'
DISCOVER = 'discover'
ELO = 'elo'
VISA = 'visa'

CARD_BRANDS = (MASTERCARD, DINERS, DISCOVER, ELO, VISA)


CREDITO_A_VISTA = '1'
PARCELADO_LOJA = '2'
PARCELADO_ADMINISTRADORA = '3'
DEBITO = 'A'

PRODUCTS = (
    CREDITO_A_VISTA,
    PARCELADO_LOJA,
    PARCELADO_ADMINISTRADORA,
    DEBITO,
)

NAO_INFORMADO = 'nao-informado'
ILEGIVEL = 'ilegivel'
INEXISTENTE = 'inexistente'
INFORMADO = 'informado'

ST_CRIADA = 0
ST_EM_ANDAMENTO = 1
ST_AUTENTICADA = 2
ST_NAO_AUTENTICADA = 3
ST_AUTORIZADA = 4
ST_NAO_AUTORIZADA = 5
ST_CAPTURADA = 6
ST_NAO_CAPTURADA = 8
ST_CANCELADA = 9
ST_EM_AUTENTICACAO = 10

STATUS = (
    ST_CRIADA,
    ST_EM_ANDAMENTO,
    ST_AUTENTICADA,
    ST_NAO_AUTENTICADA,
    ST_AUTORIZADA,
    ST_NAO_AUTORIZADA,
    ST_CAPTURADA,
    ST_NAO_CAPTURADA,
    ST_CANCELADA,
    ST_EM_AUTENTICACAO,
)


DEFAULT_CURRENCY = '096'


class Order(object):
    def __init__(self, value, number, datetime, description=None,
                 currency=DEFAULT_CURRENCY, language='PT'):
        self.value = value
        self.number = number
        self.datetime = datetime
        self.currency = currency
        self.description = description
        self.language = language


class Payment(object):
    def __init__(self, value, datetime, installments, brand):
        self.value = value
        self.datetime = datetime
        self.installments = installments
        self.brand = brand


class CardData(object):
    def __init__(self, number, holder_name, expiration_date, security_code):
        self.number = number
        self.holder_name = holder_name
        self.expiration_date = expiration_date
        self.security_code = security_code


class DebitPayment(Payment):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('installments', 1)
        super(Payment, self).__init__(*args, **kwargs)


class ContentType(object):
    pass


class Response(object):
    @property
    def success(self):
        return not isinstance(self, Error)


class Transaction(Response):
    def __init__(self, order, status, authentication=None,
                 authorization=None, capture=None, cancel=None, pan=None):
        self.order = order
        #self.payment = payment
        self.status = status
        self.authentication = authentication
        self.authorization = authorization
        self.capture = capture
        self.cancel = cancel
        self.pan = pan

    @classmethod
    def deserialize(cls, appstruct):
        order = Order(**appstruct['order'])
        return cls(order=order, status=appstruct['status'])


class Error(Response):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    @classmethod
    def deserialize(cls, appstruct):
        return cls(**appstruct)


class SecurityCodeIndicator(colander.Integer):
    map = dict((
        (NAO_INFORMADO, 0),
        (INFORMADO, 1),
        (ILEGIVEL, 2),
        (INEXISTENTE, 9),
    ))
    _rmap = dict((b, a) for (a, b) in map.iteritems())

    def serialize(self, node, appstruct):
        i = self.map.get(appstruct, None)
        if i is None:
            raise colander.Invalid(node, "%s is not a valid SecuirtyCodeIndicator" % appstruct)
        return super(SecurityCodeIndicator, self).serialize(node, i)

    def deserialize(self, node, cstruct):
        i = super(SecurityCodeIndicator, self).deserialize(node, cstruct)

        if i is colander.null:
            return i

        appstruct = self._rmap.get(i, None)

        if appstruct is None:
            raise colander.Invalid(node, "%s is not a valid SecurityCodeIndicator" % i)

        return appstruct


class Money(colander.Decimal):
    """
    Serializes python numeric values.

    Note that valid monetary values should not have more than two
    decimal places.

    ::

        >>> node = colander.SchemaNode(Money())
        >>> node.serialize(200)
        '20000'
        >>> node.serialize(200.0)
        '20000'
        >>> node.serialize(199.5)
        '19950'
        >>> node.serialize(200.21)
        '20021'
        >>> from decimal import Decimal
        >>> node.serialize(Decimal('200'))
        '20000'
        >>> node.serialize(Decimal('200.21'))
        '20021'
        >>> node.serialize(Decimal('200.3'))
        '20030'
        >>> node.serialize(200.213)
        Traceback (most recent call last):
          ...
        Invalid: {'': u'"200.213" is not a valid Money value because it has more than two decimal places'}
        >>> node.deserialize('20000')
        Decimal('200.00')
        >>> node.deserialize('193')
        Decimal('1.93')
        >>> node.deserialize('190')
        Decimal('1.90')
    """
    def serialize(self, node, appstruct):
        cstruct = super(Money, self).serialize(node, appstruct)

        if cstruct is not colander.null:
            if '.' in cstruct:
                i, d = str(cstruct).rsplit('.', 1)
            else:
                i = str(cstruct)
                d = '00'

            if len(d) > 2:
                raise colander.Invalid(node,
                    ('"%s" is not a valid Money value because it has'
                     ' more than two decimal places' % appstruct))
            elif len(d) < 2:
                d += '0' * (2 - len(d))

            return "%s%s" % (i, d)
        else:
            return cstruct

    def deserialize(self, node, cstruct):
        if cstruct:
            cstruct = "%s.%s" % (cstruct[:-2], cstruct[-2:])
        return super(Money, self).deserialize(node, cstruct)


class BaseDateTime(colander.SchemaType):
    err_template =  "Invalid date"
    format = None

    def serialize(self, node, appstruct):
        if not appstruct:
            return colander.null

        if type(appstruct) is datetime.date: # cant use isinstance; dt subs date
            appstruct = datetime.datetime.combine(appstruct, datetime.time())

        if not isinstance(appstruct, datetime.datetime):
            raise colander.Invalid(node, '"%s" is not a datetime object' % appstruct)

        return appstruct.strftime(self.format)

    def deserialize(self, node, cstruct):
        if not cstruct:
            return colander.null
        try:
            result = self._strptime(cstruct)
        except ValueError:
            raise colander.Invalid(node, self.err_template)

        return result

    def _strptime(self, cstruct):
        """
        Deve levantar ValueError caso a estrutura seja inválida.
        """
        return datetime.datetime.strptime(cstruct, self.format)


class DateTime(BaseDateTime):
    format = "%Y-%m-%dT%H:%M:%S"

    def _strptime(self, cstruct):
        # XXX nas respostas da Cielo, os timestamps contém milisegundos
        # e timezone. precisamos tratar isso.
        try:
            return super(DateTime, self)._strptime(cstruct)
        except ValueError:
            dt, extra = cstruct.split('.', 1)
            ts = super(DateTime, self)._strptime(dt)

            # FIXME vamos fazer nosso melhor para carregar o timestamp de
            # forma correta, mas vamos ignorar o timezone
            ms, tz = extra.split('-')
            ts += datetime.timedelta(milliseconds=int(ms))
            return ts


class Month(BaseDateTime):
    err_template =  "Invalid month"
    format = "%Y%m"
    extended_format = None


class CardHolderSchema(colander.Schema):
    """
    dados-portador

    dados-portador.numero           N   R   16      Número do cartão.
    dados-portador.validade         N   R   6       Validade do cartão no formato aaaamm.
                                                    Exemplos: 201212 (dez 2012).
    dados-portador.indicador        N   R   1       Indicador do código de segurança: 0 (não informado),
                                                    1 (informado), 2 (ilegível), 9 (inexistente).
    dados-portador.codigo-seguranca N   C   3..4    Obrigatório se indicador = 1.
    dados-portador.nome-portador    AN  O   0..50   Opcional. Nome impresso no cartão.
    """
    number = colander.SchemaNode(colander.String(),
                                 tag='numero',
                                 validator=colander.Length(16, 16))
    expiration_date = colander.SchemaNode(Month(), tag='validade')
    security_code_indicator = colander.SchemaNode(SecurityCodeIndicator(),
                                                  tag='indicador')
    security_code = colander.SchemaNode(colander.String(),
                                        tag='codigo-seguranca',
                                        validator=colander.Length(3, 4))
    holder_name = colander.SchemaNode(colander.String(),
                                      tag='nome-portador',
                                      missing=colander.null,
                                      validator=colander.Length(max=50))


class OrderSchema(colander.Schema):
    """
    dados-pedido

    dados-pedido.numero     AN  R   1..20   Número do pedido da loja. Recomenda-se que seja um valor único por pedido.
    dados-pedido.valor      N   R   1..12   Valor do pedido.
    dados-pedido.moeda      N   R   3       Código numérico da moeda na ISO 4217.
                                            Para o Real, o código é 986.
    dados-pedido.data-hora  AN  R   19      Data hora do pedido.
    dados-pedido.descricao  AN  O   0..1024 Descrição do pedido.
    dados-pedido.idioma     AN  O   2       Idioma do pedido: PT (português), EN (inglês) ou ES (espanhol).
                                            Com base nessa informação é definida a língua a ser utilizada
                                            nas telas da Cielo. Caso não preenchido, assume-se PT.
    """
    number = colander.SchemaNode(colander.String(),
                                 tag='numero',
                                 validator=colander.Length(max=20))
    value = colander.SchemaNode(Money(),
                                tag='valor',
                                validator=colander.Range(
                                    min=Decimal('0.01'),
                                    max=Decimal('9999999999.99')
                                ))
    currency = colander.SchemaNode(colander.String(), tag='moeda') # TODO OneOf
    datetime = colander.SchemaNode(DateTime(), tag='data-hora')
    description = colander.SchemaNode(colander.String(),
                                      tag='descricao',
                                      validator=colander.Length(max=1024),
                                      missing=colander.null)
    language = colander.SchemaNode(colander.String(),
                                   tag='idioma',
                                   missing='PT',
                                   defaults='PT',
                                   validator=colander.OneOf(LANGUAGES))


class PaymentSchema(colander.Schema):
    """
    forma-pagamento

    forma-pagamento.bandeira    AN  R   n/a     Bandeira: visa, mastercard, diners,
                                                discover ou elo (em minúsculo).
    forma-pagamento.produto     AN  R   1       Código do produto: 1 (Crédito à Vista),
                                                2 (Parcelado loja), 3 (Parcelado administradora),
                                                A (Débito).
    forma-pagamento.parcelas    N   R   1..3    Número de parcelas. Para crédito à vista ou
                                                débito, utilizar 1.
    """
    brand = colander.SchemaNode(colander.String(),
                                tag='bandeira',
                                validator=colander.OneOf(CARD_BRANDS))
    product = colander.SchemaNode(colander.String(),
                                  tag='produto',
                                  validator=colander.OneOf(PRODUCTS))
    installments = colander.SchemaNode(colander.Integer(),
                                       tag='parcelas',
                                       validator=colander.Range(1, 999))


class EstablishmentSchema(colander.Schema):
    """
    dados-ec

    dados-ec.numero N   R   1..20   Número de afiliação da loja com a Cielo.
    dados-ec.chave  AN  R   1..100  Chave de acesso da loja atribuída pela Cielo.
    """
    number = colander.SchemaNode(colander.String(),
                                 tag='numero',
                                 validator=colander.Length(max=20))
    key = colander.SchemaNode(colander.String(),
                              tag='chave',
                              validator=colander.Length(max=100))


class AuthenticationSchema(colander.Schema):
    """Nó com dados da autenticação caso tenha passado por essa etapa.

    codigo      N   1..2    Código do processamento.
    mensagem    AN  1..100  Detalhe do processamento.
    data-hora   AN  19      Data hora do processamento.
    valor       N   1..12   Valor do processamento sem pontuação. Os dois
                            últimos dígitos são os centavos.
    eci         N   2       Nível de segurança.
    """
    tag = 'autenticacao'
    content_type = Authentication

    code = colander.SchemaNode(colander.Integer(), tag='codigo')
    message = colander.SchemaNode(colander.String(), tag='mensagem')
    datetime = colander.SchemaNode(DateTime(), tag='data-hora')
    value = colander.SchemaNode(Money(), tag='valor')
    eci = colander.SchemaNode(colander.Integer())


class AuthorizationSchema(colander.Schema):
    """Nó com dados da autorização caso tenha passado por essa etapa.

    codigo      N   1..2    Código do processamento.
    mensagem    AN  1..100  Detalhe do processamento.
    data-hora   AN  19      Data hora do processamento
    valor       N   1..12   Valor do processamento sem pontuação. Os
                            dois últimos dígitos são os centavos.
    lr          N   2       Retorno da autorização. Quando negada, é o
                            motivo da negação.
    arp         AN  6       Código da autorização caso a transação
                            tenha sido autorizada com sucesso.
    nsu         AN  6       Número de sequência da autorização. Obviamente,
                            só está disponível em transações autorizadas.
    """
    tag = 'autorizacao'
    content_type = Authorization

    code = colander.SchemaNode(colander.Integer(),
                               tag='code',
                               validator=colander.Length(max=2))
    mensagem = colander.SchemaNode(colander.String(),
                                   tag='mensagem',
                                   validator=colander.Length(max=1000))
    data = colander.SchemaNode(DateTime(), tag='data-hora')
    valor = colander.SchemaNode(Money(),
                                tag='valor',
                                validator=colander.Range(max=Decimal('9'*10 + '.99')))
    lr = colander.SchemaNode(colander.Integer(),
                             validator=colander.Length(max=2))
    nsu = colander.SchemaNode(colander.String(),
                              validator=colander.Length(max=6))
    arp = colander.SchemaNode(colander.String(),
                              missing=colander.null,
                              validator=colander.Length(max=6))


class CaptureSchema(colander.Schema):
    """Nó com dados da captura caso tenha passado por essa etapa.

    codigo      N   1..2    Código do processamento.
    mensagem    AN  1..100  Detalhe do processamento.
    data-hora   AN  19      Data hora do processamento.
    valor       N   1..12   Valor do processamento sem pontuação. Os
                            dois últimos dígitos são os centavos.
    """
    tag = 'captura'
    content_type = Capture

    code = colander.SchemaNode(colander.Integer(), tag='codigo')
    message = colander.SchemaNode(colander.String(), tag='mensagem')
    date = colander.SchemaNode(DateTime(), tag='data-hora')
    value = colander.SchemaNode(Money(), tag='valor')


class CancelSchema(colander.Schema):
    """Nó com dados do cancelamento caso tenha passado por essa etapa.

    codigo      N   1..2    Código do processamento.
    mensagem    AN  1..100  Detalhe do processamento.
    data-hora   AN  19      Data hora do processamento.
    valor       N   1..12   Valor do processamento sem pontuação. Os
                            dois últimos dígitos são os centavos.
    """
    tag = 'cancel'

    code = colander.SchemaNode(colander.Integer(), tag='codigo')
    message = colander.SchemaNode(colander.String(), tag='mensagem')
    date = colander.SchemaNode(DateTime(), tag='data-hora')
    value = colander.SchemaNode(Money(), tag='valor')


class RootNode(colander.Schema):
    """Base schema for all root nodes.
    """
    id = colander.SchemaNode(colander.String(), attrib=True)
    version = colander.SchemaNode(colander.String(), tag='versao', attrib=True)


class TransactionRequestSchema(RootNode):
    tag = 'transacao'

    establishment = EstablishmentSchema(tag='dados-ec')
    holder = CardHolderSchema(tag='dados-portador', missing=colander.null)
    order = OrderSchema(tag='dados-pedido')
    payment = PaymentSchema(tag='forma-pagamento')
    return_url = colander.SchemaNode(colander.String(), tag='url-retorno')
    authorize = colander.SchemaNode(colander.Integer(), tag='autorizar')
    capture = colander.SchemaNode(colander.Boolean(), tag='capturar', missing=colander.null)
    bin = colander.SchemaNode(colander.String(), tag='bin', missing=colander.null)


class QuerySchema(RootNode):
    """Funcionalidade de extrema importância na integração.
    É através dela que a loja virtual obtém uma “foto” da
    transação. É sempre utilizada após a loja ter recebido o
    retorno do fluxo da Cielo

    tid             AN  R   1..40   Identificador da transação.
    """
    tag = 'requisicao-consulta'

    tid = colander.SchemaNode(colander.String(),
                              validator=colander.Length(max=40))
    establishment = EstablishmentSchema(tag='dados-ec')


class OrderQuerySchema(RootNode):
    """
    numero-pedido   NA  R   1...20  Número do Pedido associado à Transação
    """
    tag = 'requisicao-consulta-chsec'

    order_number = colander.SchemaNode(colander.String(),
                                       tag='numero-pedido',
                                       validator=colander.Length(max=20))
    establishment = EstablishmentSchema(tag='dados-ec')


class CaptureRequestNode(RootNode):
    """Schema da requisição de captura.

    dados-ec.numero N   R   1..20   Número de afiliação da loja com a Cielo
    dados-ec.chave  AN  R   1..100  Chave de acesso da loja atribuída pela Cielo
    tid             AN  R   1..40   Identificador da transação.
    valor           N   O   1..12   Valor da captura. Caso não fornecido,
                                    o valor atribuído é o valor da autorização.
    anexo           AN  O   1..1024 Informação adicional para detalhamento da captura.
    """
    tag = 'requisicao-captura'

    tid = colander.SchemaNode(colander.String(),
                              validator=colander.Length(max=40))
    value = colander.SchemaNode(Money(),
                                tag='valor',
                                missing=colander.null,
                                validator=colander.Range(max=Decimal('9999999999.99')))
    attachment = colander.SchemaNode(colander.String(),
                                     tag='anexo',
                                     missing=colander.null,
                                     validator=colander.Length(max=1024))
    establishment = EstablishmentSchema(tag='dados-ec')


class ErrorSchema(colander.Schema):
    tag = 'erro'
    content_type = Error

    code = colander.SchemaNode(colander.Integer(), tag='codigo')
    message = colander.SchemaNode(colander.String(), tag='mensagem')


class TransactionSchema(RootNode):
    tag = 'transacao'
    content_type = Transaction

    tid = colander.SchemaNode(colander.String())
    order = OrderSchema(tag='dados-pedido')
    payment = PaymentSchema(tag='forma-pagamento')
    status = colander.SchemaNode(colander.Integer(), validator=colander.OneOf(STATUS))
    authentication = AuthenticationSchema(tag='autenticacao', missing=colander.null)
    authorization = AuthorizationSchema(tag='autorizacao', missing=colander.null)
    capture = CaptureSchema(tag='captura', missing=colander.null)
    cancel = CancelSchema(tag='cancelamento', missing=colander.null)
    pan = colander.SchemaNode(colander.String())
    authentication_url = colander.SchemaNode(colander.String(),
                                             tag='url-autenticacao',
                                             missing=colander.null)


def guess_response_schema(tag):
    from bbe.cielo import schema
    members = inspect.getmembers(schema)
    for (name, value) in members:
        if not isinstance(value, type):
            continue
        if not issubclass(value, colander.Schema):
            continue
        if getattr(value, 'tag', None) == tag:
            return value(tag=value.tag, content_type=value.content_type)
