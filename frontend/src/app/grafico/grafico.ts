import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  inject,
  input,
  viewChild,
} from '@angular/core';
import Plotly from 'plotly.js-dist-min';

import { Figura } from '../chat/modelos';

/**
 * Envolve o plotly.js diretamente, sem wrapper de terceiros: sao 20 linhas e
 * evita depender de uma biblioteca que costuma ficar atras das versoes do
 * Angular. A figura vem pronta do backend -- aqui so se desenha.
 */
@Component({
  selector: 'app-grafico',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #host class="grafico"></div>`,
  styles: `
    .grafico {
      width: 100%;
      /* A altura vem da figura: barras horizontais crescem com as categorias. */
      min-height: 200px;
    }
  `,
})
export class Grafico {
  readonly figura = input.required<Figura>();
  private readonly host = viewChild.required<ElementRef<HTMLDivElement>>('host');

  constructor() {
    afterRenderEffect(() => {
      const figura = this.figura();
      void Plotly.react(this.host().nativeElement, figura.data as Plotly.Data[], figura.layout, {
        responsive: true,
        displayModeBar: false,
        locale: 'pt-BR',
      });
    });

    inject(DestroyRef).onDestroy(() => Plotly.purge(this.host().nativeElement));
  }
}
