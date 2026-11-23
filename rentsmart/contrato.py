"""Taxa contratual da locação e seu parcelamento."""

from decimal import Decimal

from .dinheiro import ZERO, arredondar


class TaxaContratual:
    """Taxa única de contrato, cobrada separadamente do aluguel mensal.

    O valor de R$ 2.000,00 pode ser dividido em até 5 parcelas mensais.
    Quando a divisão não é exata (ex.: 3x), a última parcela absorve a
    diferença de centavos, para que a soma das parcelas seja sempre
    exatamente o valor total.
    """

    VALOR_TOTAL = Decimal("2000.00")
    MAXIMO_PARCELAS = 5

    def __init__(self, numero_parcelas: int):
        if not 1 <= numero_parcelas <= self.MAXIMO_PARCELAS:
            raise ValueError(
                f"A taxa contratual pode ser paga em 1 a {self.MAXIMO_PARCELAS} parcelas "
                f"(informado: {numero_parcelas})."
            )
        self.numero_parcelas = numero_parcelas

    def calcular_parcelas(self) -> list[Decimal]:
        """Lista com o valor de cada parcela, na ordem de pagamento."""
        valor_padrao = arredondar(self.VALOR_TOTAL / self.numero_parcelas)
        parcelas = [valor_padrao] * (self.numero_parcelas - 1)
        parcelas.append(self.VALOR_TOTAL - sum(parcelas, ZERO))
        return parcelas

    def valor_parcela_no_mes(self, mes: int) -> Decimal:
        """Quanto da taxa é cobrado no mês informado (1 = primeiro mês do contrato)."""
        if 1 <= mes <= self.numero_parcelas:
            return self.calcular_parcelas()[mes - 1]
        return ZERO

    def descricao_parcelamento(self) -> str:
        """Texto da condição de pagamento escolhida, ex.: "Parcelada em 3x" ou "À vista (1x)"."""
        if self.numero_parcelas == 1:
            return "À vista (1x)"
        return f"Parcelada em {self.numero_parcelas}x"
