import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Modalidade } from './modelos';

interface Campo {
  rotulo: string;
  valor: string;
}

/**
 * Glossário das modalidades do programa. Fica na coluna lateral porque é
 * material de consulta: acompanha a leitura sem disputar espaço com a resposta.
 *
 * A faixa colorida de cada verbete usa a mesma cor que a modalidade recebe nos
 * gráficos, então o glossário funciona como legenda de quem já viu o gráfico.
 */
@Component({
  selector: 'app-glossario',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './glossario.html',
  styleUrl: './glossario.css',
})
export class Glossario {
  readonly modalidades = input.required<Modalidade[]>();

  readonly verbetes = computed(() =>
    this.modalidades().map((modalidade) => ({
      ...modalidade,
      // `negociacao` e `garantia` seguem no domínio e no prompt do agente --
      // ele responde sobre elas quando perguntado; só não ocupam a lateral.
      campos: [
        { rotulo: 'Quem', valor: modalidade.publico },
        { rotulo: 'Valor', valor: modalidade.teto },
        { rotulo: 'Dívidas', valor: modalidade.dividas },
      ] satisfies Campo[],
    })),
  );
}
