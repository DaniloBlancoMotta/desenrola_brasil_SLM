/** Contrato da API. Espelha RespostaResponse do backend. */

export interface Figura {
  data: unknown[];
  layout: Record<string, unknown>;
}

export interface LinhaTabela {
  rotulo: string;
  valores: Record<string, number>;
}

export interface Tabela {
  titulo: string;
  dimensao: string;
  metrica: string;
  series: string[];
  linhas: LinhaTabela[];
}

export interface RespostaChat {
  resposta: string;
  graficos: Figura[];
  tabelas: Tabela[];
}

export interface Mensagem {
  autor: 'usuario' | 'agente';
  texto: string;
  graficos?: Figura[];
  tabelas?: Tabela[];
  erro?: boolean;
}

export interface Modalidade {
  codigo: number;
  nome: string;
  tese: string;
  publico: string;
  teto: string;
  dividas: string;
  negociacao: string;
  garantia: string;
  base_legal: string;
  cor: string;
}

/** Resumo da origem dos dados, vindo de /api/base. */
export interface Base {
  fonte: string;
  url: string;
  periodo: string;
  meses: number;
  registros: number;
  conglomerados: number;
  ufs: number;
  modalidades: Modalidade[];
  volume_total: number;
  operacoes_totais: number;
  colunas: Record<string, string>;
}
