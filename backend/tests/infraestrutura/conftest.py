from pathlib import Path

import pytest

from infraestrutura.csv_repository import RepositorioDesenrolaCSV

CSV_REAL = Path("/data/bacen_data.csv")

# Reproduz a virada de jan/2025: o mesmo banco antes como "BB" e depois como
# "BB - PRUDENCIAL", com codigos diferentes.
CSV_SINTETICO = """DATA_BASE;TIPO_DESENROLA;UNIDADE_FEDERACAO;COD_CONGLOMERADO_FINANCEIRO;NOME_CONGLOMERADO_FINANCEIRO;NUMERO_OPERACOES;VOLUME_OPERACOES
202312;1;SP;49906;BB;100;1000,50
202312;2;SP;10045;BRADESCO;50;500,25
202312;1;RJ;49906;BB;30;300,00
202312;1;SP;51626;CAIXA ECONÔMICA FEDERAL;20;200,00
202501;1;SP;80329;BB - PRUDENCIAL;80;800,00
202501;3;SP;10045;BRADESCO;10;100,00
202501;1;RJ;80329;BB - PRUDENCIAL;40;400,00
"""


@pytest.fixture
def repositorio(tmp_path: Path) -> RepositorioDesenrolaCSV:
    caminho = tmp_path / "desenrola.csv"
    caminho.write_text(CSV_SINTETICO, encoding="utf-8")
    return RepositorioDesenrolaCSV(caminho)


@pytest.fixture
def repositorio_real() -> RepositorioDesenrolaCSV:
    if not CSV_REAL.exists():
        pytest.skip("CSV real nao montado em /data")
    return RepositorioDesenrolaCSV(CSV_REAL)
