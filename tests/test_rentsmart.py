"""Testes automatizados das regras de negócio do RentSmart.

Execute na pasta do projeto com:
    python -m unittest discover -v
"""

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from rentsmart import (
    Apartamento,
    Casa,
    Estudio,
    ExportadorCSV,
    Imovel,
    InterfaceConsole,
    Orcamento,
    TaxaContratual,
)
from rentsmart.dinheiro import formatar_decimal_csv, formatar_moeda


def D(valor: str) -> Decimal:
    return Decimal(valor)


class TestApartamento(unittest.TestCase):
    def test_um_quarto_com_criancas_paga_apenas_o_aluguel_base(self):
        self.assertEqual(Apartamento(1, False, True).calcular_aluguel_mensal(), D("700.00"))

    def test_dois_quartos_adiciona_200(self):
        self.assertEqual(Apartamento(2, False, True).calcular_aluguel_mensal(), D("900.00"))

    def test_garagem_adiciona_300(self):
        self.assertEqual(Apartamento(1, True, True).calcular_aluguel_mensal(), D("1000.00"))

    def test_sem_criancas_tem_5_por_cento_de_desconto(self):
        self.assertEqual(Apartamento(1, False, False).calcular_aluguel_mensal(), D("665.00"))

    def test_desconto_aplicado_depois_dos_adicionais(self):
        apartamento = Apartamento(2, True, False)  # 700 + 200 + 300 = 1200 -> -5% = 1140
        self.assertEqual(apartamento.calcular_subtotal(), D("1200.00"))
        self.assertEqual(apartamento.listar_descontos()[0].valor, D("-60.00"))
        self.assertEqual(apartamento.calcular_aluguel_mensal(), D("1140.00"))

    def test_quantidade_de_quartos_invalida(self):
        for quartos in (0, 3):
            with self.assertRaises(ValueError):
                Apartamento(quartos, False, True)


class TestCasa(unittest.TestCase):
    def test_um_quarto_sem_garagem(self):
        self.assertEqual(Casa(1, False).calcular_aluguel_mensal(), D("900.00"))

    def test_dois_quartos_adiciona_250(self):
        self.assertEqual(Casa(2, False).calcular_aluguel_mensal(), D("1150.00"))

    def test_dois_quartos_com_garagem(self):
        self.assertEqual(Casa(2, True).calcular_aluguel_mensal(), D("1450.00"))

    def test_casa_nao_tem_desconto(self):
        self.assertEqual(Casa(2, True).listar_descontos(), [])

    def test_quantidade_de_quartos_invalida(self):
        with self.assertRaises(ValueError):
            Casa(3, False)


class TestEstudio(unittest.TestCase):
    def test_sem_estacionamento(self):
        estudio = Estudio(False)
        self.assertEqual(estudio.calcular_aluguel_mensal(), D("1200.00"))
        self.assertEqual(estudio.total_vagas, 0)

    def test_pacote_com_duas_vagas(self):
        estudio = Estudio(True)
        self.assertEqual(estudio.calcular_aluguel_mensal(), D("1450.00"))
        self.assertEqual(estudio.total_vagas, 2)

    def test_vagas_adicionais_custam_60_cada(self):
        estudio = Estudio(True, 3)  # 1200 + 250 + 3 x 60 = 1630
        self.assertEqual(estudio.calcular_aluguel_mensal(), D("1630.00"))
        self.assertEqual(estudio.total_vagas, 5)

    def test_vagas_adicionais_exigem_pacote(self):
        with self.assertRaises(ValueError):
            Estudio(False, 1)

    def test_vagas_adicionais_negativas(self):
        with self.assertRaises(ValueError):
            Estudio(True, -1)


class TestImovelAbstrato(unittest.TestCase):
    def test_imovel_generico_nao_pode_ser_criado(self):
        with self.assertRaises(TypeError):
            Imovel()


class TestTaxaContratual(unittest.TestCase):
    def test_soma_das_parcelas_e_sempre_2000(self):
        for numero_parcelas in range(1, 6):
            parcelas = TaxaContratual(numero_parcelas).calcular_parcelas()
            self.assertEqual(len(parcelas), numero_parcelas)
            self.assertEqual(sum(parcelas), D("2000.00"))

    def test_divisao_nao_exata_ajusta_ultima_parcela(self):
        self.assertEqual(
            TaxaContratual(3).calcular_parcelas(),
            [D("666.67"), D("666.67"), D("666.66")],
        )

    def test_parcela_so_e_cobrada_nos_primeiros_meses(self):
        taxa = TaxaContratual(5)
        self.assertEqual(taxa.valor_parcela_no_mes(1), D("400.00"))
        self.assertEqual(taxa.valor_parcela_no_mes(5), D("400.00"))
        self.assertEqual(taxa.valor_parcela_no_mes(6), D("0.00"))

    def test_numero_de_parcelas_invalido(self):
        for numero_parcelas in (0, 6):
            with self.assertRaises(ValueError):
                TaxaContratual(numero_parcelas)


class TestOrcamento(unittest.TestCase):
    def setUp(self):
        self.orcamento = Orcamento("Maria", Apartamento(2, True, False), TaxaContratual(3))

    def test_projecao_tem_12_meses(self):
        projecao = self.orcamento.gerar_projecao()
        self.assertEqual([linha.mes for linha in projecao], list(range(1, 13)))

    def test_meses_com_e_sem_parcela_da_taxa(self):
        projecao = self.orcamento.gerar_projecao()
        self.assertEqual(projecao[0].total_mes, D("1806.67"))  # 1140,00 + 666,67
        self.assertEqual(projecao[2].total_mes, D("1806.66"))  # 1140,00 + 666,66
        self.assertEqual(projecao[3].total_mes, D("1140.00"))  # sem parcela

    def test_total_do_primeiro_ano(self):
        # 12 x 1140,00 + 2000,00 = 15680,00
        self.assertEqual(self.orcamento.calcular_total_primeiro_ano(), D("15680.00"))

    def test_nome_do_cliente_obrigatorio(self):
        with self.assertRaises(ValueError):
            Orcamento("   ", Casa(1, False), TaxaContratual(1))


class TestExportadorCSV(unittest.TestCase):
    def test_gera_csv_com_cabecalho_e_12_meses(self):
        orcamento = Orcamento("João", Casa(2, True), TaxaContratual(2))
        with tempfile.TemporaryDirectory() as pasta:
            caminho = ExportadorCSV(pasta).exportar(orcamento, "teste.csv")
            with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
                linhas = list(csv.reader(arquivo, delimiter=";"))

        self.assertEqual(linhas[0], list(ExportadorCSV.CABECALHO))
        self.assertEqual(len(linhas), 13)  # cabeçalho + 12 meses
        self.assertEqual(linhas[1], ["1", "1450,00", "1000,00", "2450,00", "2450,00"])
        self.assertEqual(linhas[3], ["3", "1450,00", "0,00", "1450,00", "6350,00"])
        self.assertEqual(linhas[12][4], "19400,00")  # 12 x 1450 + 2000

    def test_nome_do_arquivo_sem_acentos_nem_espacos(self):
        nome = ExportadorCSV._gerar_nome_arquivo("José da Silva")
        self.assertTrue(nome.startswith("projecao_jose-da-silva_"))
        self.assertTrue(nome.endswith(".csv"))


class TestFormatacao(unittest.TestCase):
    def test_formatar_moeda(self):
        self.assertEqual(formatar_moeda(D("1140")), "R$ 1.140,00")
        self.assertEqual(formatar_moeda(D("666.666")), "R$ 666,67")
        self.assertEqual(formatar_moeda(D("-60")), "-R$ 60,00")

    def test_formatar_decimal_csv(self):
        self.assertEqual(formatar_decimal_csv(D("15680")), "15680,00")


class TestInterfaceConsole(unittest.TestCase):
    """Simula um atendimento completo, incluindo respostas inválidas."""

    def test_atendimento_completo_com_entradas_invalidas(self):
        respostas = iter(
            [
                "",  # nome vazio -> inválido
                "123",  # só números -> inválido
                "Maria Souza",
                "4",  # opção de imóvel inexistente -> inválido
                "1",  # apartamento
                "três",  # não é número -> inválido
                "2",  # 2 quartos
                "talvez",  # resposta inválida
                "s",  # com garagem
                "n",  # sem crianças
                "7",  # parcelas fora do intervalo -> inválido
                "3",  # 3 parcelas
                "n",  # não fazer novo orçamento
            ]
        )
        mensagens = []
        with tempfile.TemporaryDirectory() as pasta:
            interface = InterfaceConsole(
                ExportadorCSV(pasta),
                ler=lambda _mensagem: next(respostas),
                escrever=mensagens.append,
            )
            interface.executar()
            arquivos = list(Path(pasta).glob("projecao_maria-souza_*.csv"))
            self.assertEqual(len(arquivos), 1)

        saida = "\n".join(mensagens)
        self.assertEqual(saida.count("[!]"), 6)  # uma mensagem para cada resposta inválida
        self.assertIn("R$ 1.140,00", saida)
        self.assertIn("R$ 15.680,00", saida)


if __name__ == "__main__":
    unittest.main()
