"""Funções auxiliares para trabalhar com valores monetários.

Todos os valores em dinheiro do sistema usam ``Decimal`` em vez de ``float``.
Com ``float``, contas simples geram erros de arredondamento
(ex.: 0.1 + 0.2 = 0.30000000000000004), o que não é aceitável em um orçamento.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")


def arredondar(valor: Decimal) -> Decimal:
    """Arredonda o valor para centavos (2 casas decimais)."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def formatar_moeda(valor: Decimal) -> str:
    """Formata o valor no padrão brasileiro.

    Exemplo: Decimal("1140") -> "R$ 1.140,00"
    """
    texto = f"{abs(arredondar(valor)):,.2f}"  # "1,140.00"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")  # "1.140,00"
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"


def formatar_decimal_csv(valor: Decimal) -> str:
    """Formata o número para o CSV: vírgula decimal e sem separador de milhar.

    Exemplo: Decimal("1140") -> "1140,00"
    """
    return f"{arredondar(valor):.2f}".replace(".", ",")
