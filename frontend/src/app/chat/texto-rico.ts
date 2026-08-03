import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

interface Segmento {
  texto: string;
  forte: boolean;
}

const NEGRITO = /\*\*(.+?)\*\*/g;

/**
 * Renderiza o pouco de markdown que o modelo ainda produz -- na pratica so
 * negrito. Segmenta o texto e usa <strong> de verdade, em vez de innerHTML:
 * sem biblioteca externa e sem superficie para injecao de HTML.
 */
@Component({
  selector: 'app-texto-rico',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@for (segmento of segmentos(); track $index) {
    @if (segmento.forte) {
      <strong>{{ segmento.texto }}</strong>
    } @else {
      {{ segmento.texto }}
    }
  }`,
  styles: `
    :host {
      white-space: pre-wrap;
    }
  `,
})
export class TextoRico {
  readonly texto = input.required<string>();

  readonly segmentos = computed<Segmento[]>(() => {
    const bruto = this.texto();
    const partes: Segmento[] = [];
    let cursor = 0;

    for (const achado of bruto.matchAll(NEGRITO)) {
      const inicio = achado.index ?? 0;
      if (inicio > cursor) {
        partes.push({ texto: bruto.slice(cursor, inicio), forte: false });
      }
      partes.push({ texto: achado[1], forte: true });
      cursor = inicio + achado[0].length;
    }

    if (cursor < bruto.length) {
      partes.push({ texto: bruto.slice(cursor), forte: false });
    }
    return partes;
  });
}
