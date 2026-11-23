"""Hierarquia de imóveis da R.M Imóveis.

A classe abstrata ``Imovel`` define o algoritmo geral do aluguel:

    aluguel mensal = aluguel-base + adicionais - descontos

Cada subclasse informa apenas o que muda no seu tipo de imóvel
(valores, adicionais e descontos). Assim, o cálculo é escrito uma única vez
e cada regra comercial fica na classe a que pertence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import ZERO, arredondar, formatar_moeda


@dataclass(frozen=True)
class ItemOrcamento:
    """Uma linha da composição do aluguel, como "Vaga de garagem: R$ 300,00".

    Valores positivos são acréscimos e valores negativos são descontos.
    """

    descricao: str
    valor: Decimal


def somar_itens(itens: list[ItemOrcamento]) -> Decimal:
    """Soma os valores de uma lista de itens do orçamento."""
    return sum((item.valor for item in itens), ZERO)


class Imovel(ABC):
    """Representa qualquer imóvel disponível para locação.

    É uma classe abstrata: não existe "imóvel genérico" no catálogo da
    imobiliária, apenas apartamentos, casas e estúdios.
    """

    NOME: str  # definido em cada subclasse
    ALUGUEL_BASE: Decimal  # definido em cada subclasse

    @abstractmethod
    def descricao(self) -> str:
        """Texto curto com as características escolhidas pelo cliente."""

    @abstractmethod
    def listar_adicionais(self) -> list[ItemOrcamento]:
        """Acréscimos mensais que dependem das escolhas do cliente."""

    def listar_descontos(self) -> list[ItemOrcamento]:
        """Descontos mensais. Por padrão, o imóvel não tem desconto."""
        return []

    def item_aluguel_base(self) -> ItemOrcamento:
        """Primeira linha da composição do aluguel."""
        return ItemOrcamento(f"Aluguel-base ({self.NOME.lower()})", self.ALUGUEL_BASE)

    def calcular_subtotal(self) -> Decimal:
        """Aluguel-base somado a todos os adicionais."""
        return self.ALUGUEL_BASE + somar_itens(self.listar_adicionais())

    def calcular_aluguel_mensal(self) -> Decimal:
        """Valor final do aluguel: subtotal com os descontos aplicados."""
        return arredondar(self.calcular_subtotal() + somar_itens(self.listar_descontos()))


class ImovelComQuartos(Imovel):
    """Base comum para imóveis com 1 ou 2 quartos e opção de vaga de garagem.

    Apartamentos e casas seguem as mesmas regras de quartos e garagem e mudam
    apenas os valores. Esta classe evita repetir essa lógica nas duas.
    Ela não deve ser instanciada diretamente: use ``Apartamento`` ou ``Casa``.
    """

    QUARTOS_PERMITIDOS = (1, 2)
    VALOR_VAGA_GARAGEM = Decimal("300.00")
    ADICIONAL_SEGUNDO_QUARTO: Decimal  # definido em cada subclasse

    def __init__(self, quartos: int, possui_garagem: bool):
        if quartos not in self.QUARTOS_PERMITIDOS:
            raise ValueError(f"{self.NOME} deve ter 1 ou 2 quartos (informado: {quartos}).")
        self.quartos = quartos
        self.possui_garagem = possui_garagem

    def listar_adicionais(self) -> list[ItemOrcamento]:
        adicionais = []
        if self.quartos == 2:
            adicionais.append(ItemOrcamento("Adicional por 2 quartos", self.ADICIONAL_SEGUNDO_QUARTO))
        if self.possui_garagem:
            adicionais.append(ItemOrcamento("Vaga de garagem", self.VALOR_VAGA_GARAGEM))
        return adicionais

    def descricao(self) -> str:
        quartos = "1 quarto" if self.quartos == 1 else "2 quartos"
        garagem = "com vaga de garagem" if self.possui_garagem else "sem vaga de garagem"
        return f"{self.NOME} - {quartos}, {garagem}"


class Apartamento(ImovelComQuartos):
    """Apartamento: aluguel-base de R$ 700,00 e 2º quarto por + R$ 200,00.

    Clientes sem crianças recebem 5% de desconto sobre o aluguel já somado
    aos adicionais (quartos e garagem).
    """

    NOME = "Apartamento"
    ALUGUEL_BASE = Decimal("700.00")
    ADICIONAL_SEGUNDO_QUARTO = Decimal("200.00")
    PERCENTUAL_DESCONTO_SEM_CRIANCAS = Decimal("0.05")

    def __init__(self, quartos: int, possui_garagem: bool, possui_criancas: bool):
        super().__init__(quartos, possui_garagem)
        self.possui_criancas = possui_criancas

    def listar_descontos(self) -> list[ItemOrcamento]:
        if self.possui_criancas:
            return []
        desconto = arredondar(self.calcular_subtotal() * self.PERCENTUAL_DESCONTO_SEM_CRIANCAS)
        percentual = f"{self.PERCENTUAL_DESCONTO_SEM_CRIANCAS:.0%}"
        return [ItemOrcamento(f"Desconto de {percentual} (cliente sem crianças)", -desconto)]

    def descricao(self) -> str:
        criancas = "com crianças" if self.possui_criancas else "sem crianças"
        return f"{super().descricao()}, {criancas}"


class Casa(ImovelComQuartos):
    """Casa: aluguel-base de R$ 900,00 e 2º quarto por + R$ 250,00."""

    NOME = "Casa"
    ALUGUEL_BASE = Decimal("900.00")
    ADICIONAL_SEGUNDO_QUARTO = Decimal("250.00")


class Estudio(Imovel):
    """Estúdio: aluguel-base de R$ 1.200,00 e regra própria de estacionamento.

    O pacote inicial custa R$ 250,00 e inclui 2 vagas. Com o pacote contratado,
    o cliente pode incluir vagas adicionais por R$ 60,00 cada.
    """

    NOME = "Estúdio"
    ALUGUEL_BASE = Decimal("1200.00")
    VALOR_PACOTE_ESTACIONAMENTO = Decimal("250.00")
    VAGAS_NO_PACOTE = 2
    VALOR_VAGA_ADICIONAL = Decimal("60.00")

    def __init__(self, possui_pacote_estacionamento: bool, vagas_adicionais: int = 0):
        if vagas_adicionais < 0:
            raise ValueError("A quantidade de vagas adicionais não pode ser negativa.")
        if vagas_adicionais > 0 and not possui_pacote_estacionamento:
            raise ValueError("Vagas adicionais exigem a contratação do pacote inicial de 2 vagas.")
        self.possui_pacote_estacionamento = possui_pacote_estacionamento
        self.vagas_adicionais = vagas_adicionais

    @property
    def total_vagas(self) -> int:
        """Quantidade total de vagas de estacionamento do estúdio."""
        if not self.possui_pacote_estacionamento:
            return 0
        return self.VAGAS_NO_PACOTE + self.vagas_adicionais

    def listar_adicionais(self) -> list[ItemOrcamento]:
        adicionais = []
        if self.possui_pacote_estacionamento:
            adicionais.append(
                ItemOrcamento(
                    f"Pacote de estacionamento ({self.VAGAS_NO_PACOTE} vagas)",
                    self.VALOR_PACOTE_ESTACIONAMENTO,
                )
            )
        if self.vagas_adicionais > 0:
            adicionais.append(
                ItemOrcamento(
                    f"Vagas adicionais ({self.vagas_adicionais} x {formatar_moeda(self.VALOR_VAGA_ADICIONAL)})",
                    self.VALOR_VAGA_ADICIONAL * self.vagas_adicionais,
                )
            )
        return adicionais

    def descricao(self) -> str:
        if not self.possui_pacote_estacionamento:
            return f"{self.NOME} - sem estacionamento"
        return f"{self.NOME} - {self.total_vagas} vagas de estacionamento"
