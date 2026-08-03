import { Injectable, signal } from '@angular/core';

/**
 * Exporta a conversa em PDF pela impressão do navegador.
 *
 * Sem biblioteca de PDF: o diálogo "Salvar como PDF" já produz um arquivo com
 * texto selecionável e tabelas de verdade, enquanto um gerador no cliente
 * custaria centenas de KB e rasterizaria os gráficos. O sinal `imprimindo`
 * existe porque as tabelas mostram apenas as primeiras linhas na tela — no PDF
 * elas precisam sair inteiras.
 */
@Injectable({ providedIn: 'root' })
export class ImpressaoService {
  readonly imprimindo = signal(false);

  async exportar(): Promise<void> {
    this.imprimindo.set(true);
    // Dá um quadro ao Angular para expandir as tabelas antes do diálogo abrir,
    // que é síncrono e congela o que estiver na tela naquele instante.
    await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 60)));
    try {
      window.print();
    } finally {
      this.imprimindo.set(false);
    }
  }
}
