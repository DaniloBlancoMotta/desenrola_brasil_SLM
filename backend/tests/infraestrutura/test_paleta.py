"""A paleta e validada por script (validate_palette.js); aqui travamos o contrato.

O que estes testes protegem sao as decisoes que o validador nao ve: que a ordem
dos slots nao mude e que ninguem reintroduza a ciclagem de cores.
"""

import pytest

from infraestrutura import paleta


class TestPaletaCategorica:
    def test_ordem_dos_slots_e_congelada(self):
        """A ordem passou na validacao par a par; reordenar invalida o resultado."""
        assert paleta.SERIES[:3] == ("#2a78d6", "#eb6834", "#1baf7a")

    def test_oito_slots(self):
        assert len(paleta.SERIES) == 8

    def test_nao_ha_cor_repetida(self):
        assert len(set(paleta.SERIES)) == len(paleta.SERIES)

    def test_paleta_antiga_nao_voltou(self):
        """#16a34a x #dc2626 colapsavam a delta-E 5.0 sob deuteranopia."""
        assert "#16a34a" not in paleta.SERIES
        assert "#dc2626" not in paleta.SERIES


class TestAtribuicaoDeCor:
    def test_series_recebem_slots_em_sequencia(self):
        assert [paleta.cor_da_serie(i) for i in range(3)] == list(paleta.SERIES[:3])

    def test_nao_cicla_apos_o_ultimo_slot(self):
        """Ciclar repetiria a cor da serie 1 na serie 9 e quebraria a identidade."""
        with pytest.raises(IndexError, match="agrupada"):
            paleta.cor_da_serie(len(paleta.SERIES))


class TestCoresDeMarca:
    def test_banco_conhecido_usa_a_cor_da_instituicao(self):
        cores = paleta.cores_das_categorias(["BRADESCO", "ITAU", "NUBANK"])
        assert cores == ["#CC092F", "#EC7000", "#820AD1"]

    def test_nome_acentuado_como_vem_do_csv_encontra_a_marca(self):
        """O rotulo exibido preserva o acento; sem canonizar, a Caixa perdia a cor."""
        assert paleta.cores_das_categorias(["CAIXA ECONÔMICA FEDERAL"]) == ["#0057A6"]

    def test_sufixo_prudencial_nao_impede_a_marca(self):
        """A grafia pos jan/2025 do BCB precisa achar a mesma instituicao."""
        assert paleta.cores_das_categorias(["BB - PRUDENCIAL"]) == ["#E8B500"]

    def test_bv_e_votorantim_sao_a_mesma_instituicao(self):
        assert paleta.cores_das_categorias(["VOTORANTIM"]) == paleta.cores_das_categorias(["BV"])

    def test_banco_sem_marca_cai_nos_slots_validados(self):
        cores = paleta.cores_das_categorias(["BANRISUL", "BMG"])
        assert cores == [paleta.SERIES[0], paleta.SERIES[1]]

    def test_marca_nao_consome_slot_de_reserva(self):
        """Senao os bancos regionais receberiam cores fora de ordem."""
        cores = paleta.cores_das_categorias(["BRADESCO", "BANRISUL"])
        assert cores == ["#CC092F", paleta.SERIES[0]]

    def test_cauda_longa_recebe_neutro_em_vez_de_repetir_cor(self):
        """Repetir um slot faria dois bancos parecerem o mesmo."""
        sem_marca = [f"COOP {i}" for i in range(len(paleta.SERIES) + 3)]
        cores = paleta.cores_das_categorias(sem_marca)
        assert cores[-3:] == [paleta.NEUTRO] * 3
        assert len(set(cores[: len(paleta.SERIES)])) == len(paleta.SERIES)

    def test_preto_do_c6_nao_e_preto_puro(self):
        """#000000 compete com a tinta do texto e some contra o eixo."""
        assert paleta.CORES_DE_MARCA["C6 BANK"] != "#000000"

    def test_caixa_e_btg_nao_dividem_o_mesmo_azul(self):
        """Ambos foram pedidos como 'azul escuro'; precisam ser distinguiveis."""
        assert paleta.CORES_DE_MARCA["CAIXA ECONOMICA FEDERAL"] != paleta.CORES_DE_MARCA["BTG PACTUAL"]


class TestTokensDeChrome:
    def test_tinta_e_distinta_das_series(self):
        """Texto usa tokens de tinta, nunca a cor do dado."""
        for token in (paleta.INK_PRIMARIO, paleta.INK_SECUNDARIO, paleta.INK_MUTED):
            assert token not in paleta.SERIES

    def test_espacadores_usam_a_cor_da_superficie(self):
        assert paleta.SUPERFICIE == "#ffffff"

    def test_marcas_seguem_as_especificacoes(self):
        assert paleta.ESPESSURA_LINHA == 2
        assert paleta.TAMANHO_MARCADOR >= 8
        assert paleta.ANEL_SUPERFICIE == 2
