"""Orçamento de locação: reúne cliente, imóvel e taxa contratual."""

from dataclasses import dataclass
from decimal import Decimal

from .contrato import TaxaContratual
from .dinheiro import ZERO
from .imoveis import Imovel


@dataclass(frozen=True)
class ProjecaoMensal:
    """Valores previstos para um mês do contrato."""

    mes: int
    aluguel: Decimal
    parcela_taxa: Decimal
    total_mes: Decimal
    total_acumulado: Decimal


class Orcamento:
    """Orçamento de locação de um cliente.

    O aluguel mensal e a taxa contratual ficam em objetos separados, para que
    os dois custos nunca sejam confundidos. Eles só são somados na projeção
    mês a mês, que mostra quanto o cliente pagará em cada mês do 1º ano.
    """

    MESES_PROJECAO = 12

    def __init__(self, cliente: str, imovel: Imovel, taxa_contratual: TaxaContratual):
        cliente = cliente.strip()
        if not cliente:
            raise ValueError("O nome do cliente é obrigatório.")
        self.cliente = cliente
        self.imovel = imovel
        self.taxa_contratual = taxa_contratual

    @property
    def aluguel_mensal(self) -> Decimal:
        """Valor mensal do aluguel, já com adicionais e descontos."""
        return self.imovel.calcular_aluguel_mensal()

    def gerar_projecao(self) -> list[ProjecaoMensal]:
        """Projeção dos 12 primeiros meses: aluguel + parcela da taxa (se houver)."""
        aluguel = self.aluguel_mensal
        acumulado = ZERO
        projecao = []
        for mes in range(1, self.MESES_PROJECAO + 1):
            parcela = self.taxa_contratual.valor_parcela_no_mes(mes)
            total_mes = aluguel + parcela
            acumulado += total_mes
            projecao.append(ProjecaoMensal(mes, aluguel, parcela, total_mes, acumulado))
        return projecao

    def calcular_total_primeiro_ano(self) -> Decimal:
        """Soma de tudo o que o cliente pagará nos 12 primeiros meses."""
        return self.gerar_projecao()[-1].total_acumulado
