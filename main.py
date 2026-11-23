"""Ponto de entrada do RentSmart.

Execute na pasta do projeto com:
    python main.py
"""

from pathlib import Path

from rentsmart import ExportadorCSV, InterfaceConsole

# Os arquivos CSV são gravados na pasta "saida", ao lado deste arquivo.
PASTA_SAIDA = Path(__file__).resolve().parent / "saida"


def main() -> None:
    interface = InterfaceConsole(ExportadorCSV(PASTA_SAIDA))
    try:
        interface.executar()
    except (KeyboardInterrupt, EOFError):
        print("\n\nAtendimento encerrado pelo usuário.")


if __name__ == "__main__":
    main()
