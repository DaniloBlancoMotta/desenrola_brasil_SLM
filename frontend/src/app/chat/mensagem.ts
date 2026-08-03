import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Grafico } from '../grafico/grafico';
import { Mensagem as ModeloMensagem } from './modelos';
import { Tabela } from './tabela';
import { TextoRico } from './texto-rico';

@Component({
  selector: 'app-mensagem',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Grafico, Tabela, TextoRico],
  template: `
    <article class="linha" [class.propria]="mensagem().autor === 'usuario'">
      <div class="bolha" [class.erro]="mensagem().erro" [class.larga]="temAnexo()">
        <app-texto-rico [texto]="mensagem().texto" />

        @for (grafico of mensagem().graficos ?? []; track $index) {
          <app-grafico [figura]="grafico" />
        }

        @for (tabela of mensagem().tabelas ?? []; track $index) {
          <app-tabela [tabela]="tabela" />
        }
      </div>
    </article>
  `,
  styles: `
    .linha {
      display: flex;
      margin-bottom: 1rem;
    }

    .linha.propria {
      justify-content: flex-end;
    }

    .bolha {
      max-width: min(46rem, 88%);
      padding: 0.7rem 1rem;
      border: 1px solid var(--borda);
      border-radius: 0.9rem;
      background: var(--superficie);
    }

    /* Grafico e tabela precisam de largura; a bolha so se expande quando ha um. */
    .bolha.larga {
      width: min(46rem, 92%);
    }

    .propria .bolha {
      background: var(--acento);
      border-color: var(--acento);
      color: #fff;
    }

    .bolha.erro {
      border-color: var(--erro);
      color: var(--erro);
    }

    app-grafico {
      display: block;
      margin-top: 0.75rem;
    }
  `,
})
export class Mensagem {
  readonly mensagem = input.required<ModeloMensagem>();

  temAnexo(): boolean {
    const mensagem = this.mensagem();
    return Boolean(mensagem.graficos?.length || mensagem.tabelas?.length);
  }
}
