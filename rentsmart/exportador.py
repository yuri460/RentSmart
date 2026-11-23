"""Exportação da projeção de 12 meses para arquivo CSV."""

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .dinheiro import formatar_decimal_csv
from .orcamento import Orcamento


class ExportadorCSV:
    """Gera o arquivo CSV com a projeção mensal de um orçamento.

    O arquivo segue o padrão brasileiro (separador ";" e vírgula decimal) e
    usa codificação UTF-8 com BOM, para abrir corretamente no Excel e manter
    os acentos.
    """

    CABECALHO = (
        "Mês",
        "Aluguel (R$)",
        "Parcela da taxa contratual (R$)",
        "Total do mês (R$)",
        "Total acumulado (R$)",
    )

    def __init__(self, pasta_destino: Union[str, Path], separador: str = ";"):
        self.pasta_destino = Path(pasta_destino)
        self.separador = separador

    def exportar(self, orcamento: Orcamento, nome_arquivo: Optional[str] = None) -> Path:
        """Grava a projeção no CSV e devolve o caminho do arquivo criado."""
        self.pasta_destino.mkdir(parents=True, exist_ok=True)
        caminho = self.pasta_destino / (nome_arquivo or self._gerar_nome_arquivo(orcamento.cliente))

        with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=self.separador)
            escritor.writerow(self.CABECALHO)
            for linha in orcamento.gerar_projecao():
                escritor.writerow(
                    [
                        linha.mes,
                        formatar_decimal_csv(linha.aluguel),
                        formatar_decimal_csv(linha.parcela_taxa),
                        formatar_decimal_csv(linha.total_mes),
                        formatar_decimal_csv(linha.total_acumulado),
                    ]
                )
        return caminho

    @staticmethod
    def _gerar_nome_arquivo(cliente: str) -> str:
        """Ex.: "projecao_maria-souza_20261123_153012.csv"."""
        sem_acentos = unicodedata.normalize("NFKD", cliente).encode("ascii", "ignore").decode("ascii")
        identificador = re.sub(r"[^a-z0-9]+", "-", sem_acentos.lower()).strip("-") or "cliente"
        data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"projecao_{identificador}_{data_hora}.csv"
