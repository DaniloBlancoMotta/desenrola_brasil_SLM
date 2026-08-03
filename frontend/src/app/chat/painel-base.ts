import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { Base } from './modelos';

/**
 * Diz de onde vêm os números que a conversa exibe. Fica recolhido por padrão:
 * a procedência importa, mas não deve competir com a resposta.
 */
@Component({
  selector: 'app-painel-base',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './painel-base.html',
  styleUrl: './painel-base.css',
})
export class PainelBase {
  readonly base = input.required<Base>();
  readonly aberto = signal(false);

  readonly resumo = computed(() => {
    const base = this.base();
    return [
      { rotulo: 'Período', valor: base.periodo, detalhe: `${base.meses} meses` },
      {
        rotulo: 'Instituições',
        valor: this.inteiro(base.conglomerados),
        detalhe: 'conglomerados',
      },
      { rotulo: 'Abrangência', valor: `${base.ufs} UFs`, detalhe: 'todo o país' },
      {
        rotulo: 'Volume total',
        valor: this.compacto(base.volume_total),
        detalhe: `${this.compacto(base.operacoes_totais, false)} operações`,
      },
    ];
  });

  readonly colunas = computed(() => Object.entries(this.base().colunas));

  alternar(): void {
    this.aberto.update((atual) => !atual);
  }

  private inteiro(valor: number): string {
    return valor.toLocaleString('pt-BR');
  }

  private compacto(valor: number, moeda = true): string {
    const escalas: [number, string][] = [
      [1e9, 'bi'],
      [1e6, 'mi'],
      [1e3, 'mil'],
    ];
    for (const [limite, sufixo] of escalas) {
      if (Math.abs(valor) >= limite) {
        const numero = (valor / limite).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
        return `${moeda ? 'R$ ' : ''}${numero} ${sufixo}`;
      }
    }
    return `${moeda ? 'R$ ' : ''}${this.inteiro(valor)}`;
  }
}
