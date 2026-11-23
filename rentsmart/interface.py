"""Interface de console (linha de comando) do RentSmart.

Esta classe só conversa com o usuário: lê e valida as entradas, cria os
objetos do sistema e exibe os resultados. Nenhuma regra de preço fica aqui.
Os valores exibidos nas perguntas vêm das próprias classes de imóvel e da
taxa contratual, então uma mudança de preço é feita em um único lugar.
"""

from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable

from .contrato import TaxaContratual
from .dinheiro import formatar_moeda
from .exportador import ExportadorCSV
from .imoveis import Apartamento, Casa, Estudio, Imovel, ImovelComQuartos
from .orcamento import Orcamento


class InterfaceConsole:
    """Conduz o atendimento: coleta dados, mostra o orçamento e gera o CSV."""

    LARGURA = 62
    LARGURA_DESCRICAO = 40
    LIMITE_VAGAS_ADICIONAIS = 10  # limite operacional, evita erros de digitação
    RESPOSTAS_SIM = ("s", "sim")
    RESPOSTAS_NAO = ("n", "nao", "não")

    def __init__(
        self,
        exportador: ExportadorCSV,
        ler: Callable[[str], str] = input,
        escrever: Callable[[str], None] = print,
    ):
        # "ler" e "escrever" podem ser trocados nos testes automatizados.
        self.exportador = exportador
        self._ler = ler
        self._escrever = escrever
        self._tipos_imovel = {
            "1": (Apartamento, self._coletar_apartamento),
            "2": (Casa, self._coletar_casa),
            "3": (Estudio, self._coletar_estudio),
        }

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------
    def executar(self) -> None:
        """Repete o atendimento até o usuário não querer mais orçamentos."""
        self._exibir_cabecalho("RentSmart | R.M Imóveis - Orçamento de Locação")
        while True:
            orcamento = self.coletar_orcamento()
            self.exibir_orcamento(orcamento)
            caminho = self.exportador.exportar(orcamento)
            self._escrever(f"\nProjeção de 12 meses salva em: {self._caminho_amigavel(caminho)}")
            if not self._ler_sim_nao("\nDeseja fazer um novo orçamento? (s/n): "):
                break
        self._escrever("\nObrigado por utilizar o RentSmart!")

    def coletar_orcamento(self) -> Orcamento:
        """Pergunta tudo o que é necessário e monta o objeto Orcamento."""
        self._escrever("\n--- Dados do cliente ---")
        cliente = self._ler_nome("Nome do cliente: ")
        imovel = self._coletar_imovel()

        self._escrever("\n--- Taxa contratual ---")
        self._escrever(
            f"Taxa única de {formatar_moeda(TaxaContratual.VALOR_TOTAL)}, "
            f"em até {TaxaContratual.MAXIMO_PARCELAS} parcelas (cobrada à parte do aluguel)."
        )
        numero_parcelas = self._ler_inteiro(
            f"Em quantas parcelas deseja pagar? (1 a {TaxaContratual.MAXIMO_PARCELAS}): ",
            1,
            TaxaContratual.MAXIMO_PARCELAS,
        )
        return Orcamento(cliente, imovel, TaxaContratual(numero_parcelas))

    # ------------------------------------------------------------------
    # Coleta das características de cada tipo de imóvel
    # ------------------------------------------------------------------
    def _coletar_imovel(self) -> Imovel:
        self._escrever("\n--- Tipo de imóvel ---")
        for opcao, (classe, _) in self._tipos_imovel.items():
            self._escrever(f"  {opcao} - {classe.NOME:<12} aluguel-base {formatar_moeda(classe.ALUGUEL_BASE)}")
        opcao = self._ler_opcao("Escolha uma opção: ", self._tipos_imovel.keys())
        _, coletar = self._tipos_imovel[opcao]
        return coletar()

    def _coletar_apartamento(self) -> Apartamento:
        quartos, possui_garagem = self._coletar_quartos_e_garagem(Apartamento)
        percentual = f"{Apartamento.PERCENTUAL_DESCONTO_SEM_CRIANCAS:.0%}"
        possui_criancas = self._ler_sim_nao(
            f"O cliente possui crianças? (s/n) [sem crianças: {percentual} de desconto]: "
        )
        return Apartamento(quartos, possui_garagem, possui_criancas)

    def _coletar_casa(self) -> Casa:
        quartos, possui_garagem = self._coletar_quartos_e_garagem(Casa)
        return Casa(quartos, possui_garagem)

    def _coletar_quartos_e_garagem(self, classe: type[ImovelComQuartos]) -> tuple[int, bool]:
        """Perguntas comuns a apartamentos e casas (mudam apenas os valores)."""
        minimo, maximo = min(classe.QUARTOS_PERMITIDOS), max(classe.QUARTOS_PERMITIDOS)
        quartos = self._ler_inteiro(
            f"Quantidade de quartos ({minimo} ou {maximo}) "
            f"[2 quartos: + {formatar_moeda(classe.ADICIONAL_SEGUNDO_QUARTO)}/mês]: ",
            minimo,
            maximo,
        )
        possui_garagem = self._ler_sim_nao(
            f"Deseja vaga de garagem? (s/n) [+ {formatar_moeda(classe.VALOR_VAGA_GARAGEM)}/mês]: "
        )
        return quartos, possui_garagem

    def _coletar_estudio(self) -> Estudio:
        possui_pacote = self._ler_sim_nao(
            f"Deseja o pacote de estacionamento com {Estudio.VAGAS_NO_PACOTE} vagas? (s/n) "
            f"[+ {formatar_moeda(Estudio.VALOR_PACOTE_ESTACIONAMENTO)}/mês]: "
        )
        vagas_adicionais = 0
        if possui_pacote:
            vagas_adicionais = self._ler_inteiro(
                f"Quantas vagas adicionais? (0 a {self.LIMITE_VAGAS_ADICIONAIS}) "
                f"[+ {formatar_moeda(Estudio.VALOR_VAGA_ADICIONAL)}/mês cada]: ",
                0,
                self.LIMITE_VAGAS_ADICIONAIS,
            )
        return Estudio(possui_pacote, vagas_adicionais)

    # ------------------------------------------------------------------
    # Exibição do orçamento
    # ------------------------------------------------------------------
    def exibir_orcamento(self, orcamento: Orcamento) -> None:
        """Mostra como o valor foi formado, a taxa contratual e a projeção."""
        imovel = orcamento.imovel
        taxa = orcamento.taxa_contratual

        self._escrever("")
        self._exibir_cabecalho("ORÇAMENTO DE LOCAÇÃO")
        self._escrever(f"Cliente: {orcamento.cliente}")
        self._escrever(f"Imóvel : {imovel.descricao()}")

        self._exibir_secao("1. Aluguel mensal")
        base = imovel.item_aluguel_base()
        self._exibir_linha(base.descricao, base.valor)
        for item in imovel.listar_adicionais():
            self._exibir_linha(item.descricao, item.valor, com_sinal=True)
        descontos = imovel.listar_descontos()
        if descontos:
            self._exibir_separador()
            self._exibir_linha("Subtotal", imovel.calcular_subtotal())
            for item in descontos:
                self._exibir_linha(item.descricao, item.valor, com_sinal=True)
        self._exibir_separador()
        self._exibir_linha("ALUGUEL MENSAL", orcamento.aluguel_mensal)

        self._exibir_secao("2. Taxa contratual (não faz parte do aluguel)")
        self._exibir_linha("Valor total da taxa", TaxaContratual.VALOR_TOTAL)
        self._exibir_par("Condição de pagamento", taxa.descricao_parcelamento())
        for numero, valor in enumerate(taxa.calcular_parcelas(), start=1):
            self._exibir_linha(f"  Parcela {numero}/{taxa.numero_parcelas} (mês {numero})", valor)

        self._exibir_secao("3. Projeção dos 12 primeiros meses")
        self._escrever(f"  {'Mês':>4}{'Aluguel':>18}{'Taxa contratual':>19}{'Total do mês':>19}")
        for linha in orcamento.gerar_projecao():
            self._escrever(
                f"  {linha.mes:>4}"
                f"{formatar_moeda(linha.aluguel):>18}"
                f"{formatar_moeda(linha.parcela_taxa):>19}"
                f"{formatar_moeda(linha.total_mes):>19}"
            )
        self._exibir_separador()
        self._exibir_linha("TOTAL PREVISTO NO 1º ANO", orcamento.calcular_total_primeiro_ano())
        self._escrever("=" * self.LARGURA)

    def _exibir_cabecalho(self, titulo: str) -> None:
        self._escrever("=" * self.LARGURA)
        self._escrever(titulo.center(self.LARGURA))
        self._escrever("=" * self.LARGURA)

    def _exibir_secao(self, titulo: str) -> None:
        self._escrever(f"\n{titulo.upper()}")

    def _exibir_separador(self) -> None:
        self._escrever("  " + "-" * (self.LARGURA - 2))

    def _exibir_linha(self, descricao: str, valor: Decimal, com_sinal: bool = False) -> None:
        """Linha com valor em reais. Com sinal: "+ R$ 300,00" ou "- R$ 60,00"."""
        texto = formatar_moeda(abs(valor) if com_sinal else valor)
        if com_sinal:
            texto = ("- " if valor < 0 else "+ ") + texto
        self._exibir_par(descricao, texto)

    def _exibir_par(self, descricao: str, texto: str) -> None:
        """Linha alinhada: descrição à esquerda e texto à direita."""
        largura_texto = self.LARGURA - 2 - self.LARGURA_DESCRICAO
        self._escrever(f"  {descricao:<{self.LARGURA_DESCRICAO}}{texto:>{largura_texto}}")

    # ------------------------------------------------------------------
    # Leitura e validação de entradas (repetem até receber valor válido)
    # ------------------------------------------------------------------
    def _ler_nome(self, mensagem: str) -> str:
        while True:
            nome = " ".join(self._ler(mensagem).split())  # remove espaços extras
            if any(caractere.isalpha() for caractere in nome):
                return nome
            self._erro("Informe um nome válido (o campo não pode ficar vazio nem conter só números).")

    def _ler_inteiro(self, mensagem: str, minimo: int, maximo: int) -> int:
        while True:
            resposta = self._ler(mensagem).strip()
            try:
                numero = int(resposta)
            except ValueError:
                self._erro("Digite um número inteiro.")
                continue
            if minimo <= numero <= maximo:
                return numero
            self._erro(f"Digite um valor entre {minimo} e {maximo}.")

    def _ler_sim_nao(self, mensagem: str) -> bool:
        while True:
            resposta = self._ler(mensagem).strip().lower()
            if resposta in self.RESPOSTAS_SIM:
                return True
            if resposta in self.RESPOSTAS_NAO:
                return False
            self._erro("Responda 's' para sim ou 'n' para não.")

    def _ler_opcao(self, mensagem: str, opcoes: Iterable[str]) -> str:
        opcoes = list(opcoes)
        while True:
            resposta = self._ler(mensagem).strip()
            if resposta in opcoes:
                return resposta
            self._erro(f"Opção inválida. Escolha uma destas: {', '.join(opcoes)}.")

    def _erro(self, mensagem: str) -> None:
        self._escrever(f"  [!] {mensagem}")

    @staticmethod
    def _caminho_amigavel(caminho: Path) -> Path:
        """Mostra o caminho relativo à pasta atual, quando possível."""
        try:
            return caminho.resolve().relative_to(Path.cwd())
        except ValueError:
            return caminho
