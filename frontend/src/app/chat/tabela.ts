import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';

import { ImpressaoService } from './impressao.service';
import { Tabela as ModeloTabela } from './modelos';

const LINHAS_VISIVEIS = 12;

/**
 * Tabela montada a partir dos dados que a API devolve, nao do texto do modelo.
 * O modelo ve um resumo truncado; esta tabela tem sempre a serie completa.
 */
@Component({
  selector: 'app-tabela',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './tabela.html',
  styleUrl: './tabela.css',
})
export class Tabela {
  private readonly impressao = inject(ImpressaoService);

  readonly tabela = input.required<ModeloTabela>();
  readonly expandida = signal(false);

  private readonly emReais = computed(() => this.tabela().metrica.includes('R$'));

  readonly linhas = computed(() => {
    const todas = this.tabela().linhas;
    // No PDF a tabela sai inteira: um recorte impresso perderia dados sem aviso.
    const completa = this.expandida() || this.impressao.imprimindo();
    return completa ? todas : todas.slice(0, LINHAS_VISIVEIS);
  });

  readonly ocultas = computed(() => this.tabela().linhas.length - this.linhas().length);

  formatar(valor: number | undefined): string {
    if (valor === undefined) {
      return '—';
    }
    const casas = this.emReais() ? 2 : 0;
    return valor.toLocaleString('pt-BR', {
      minimumFractionDigits: casas,
      maximumFractionDigits: casas,
    });
  }

  alternar(): void {
    this.expandida.update((atual) => !atual);
  }
}
