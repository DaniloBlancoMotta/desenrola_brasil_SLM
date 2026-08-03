import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  afterRenderEffect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ChatService } from './chat.service';
import { Glossario } from './glossario';
import { ImpressaoService } from './impressao.service';
import { Mensagem as MensagemComponent } from './mensagem';
import { Base, Mensagem } from './modelos';
import { PainelBase } from './painel-base';

@Component({
  selector: 'app-chat',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Glossario, MensagemComponent, PainelBase],
  templateUrl: './chat.html',
  styleUrl: './chat.css',
})
export class Chat {
  private readonly servico = inject(ChatService);
  private readonly impressao = inject(ImpressaoService);
  private readonly rolagem = viewChild.required<ElementRef<HTMLElement>>('rolagem');

  readonly mensagens = signal<Mensagem[]>([]);
  readonly carregando = signal(false);
  readonly texto = signal('');
  readonly base = signal<Base | null>(null);
  readonly confirmandoLimpeza = signal(false);

  constructor() {
    this.servico.base().subscribe({
      next: (base) => this.base.set(base),
      // A procedência é contexto, não conteúdo: sem ela o chat segue utilizável.
      error: () => this.base.set(null),
    });

    // Mantem a conversa colada no rodape a cada mensagem nova.
    afterRenderEffect(() => {
      this.mensagens();
      const elemento = this.rolagem().nativeElement;
      elemento.scrollTop = elemento.scrollHeight;
    });
  }

  enviar(): void {
    const pergunta = this.texto().trim();
    if (!pergunta || this.carregando()) {
      return;
    }

    this.confirmandoLimpeza.set(false);
    this.acrescentar({ autor: 'usuario', texto: pergunta });
    this.texto.set('');
    this.carregando.set(true);

    this.servico.perguntar(pergunta).subscribe({
      next: (resposta) => {
        this.acrescentar({
          autor: 'agente',
          texto: resposta.resposta,
          graficos: resposta.graficos,
          tabelas: resposta.tabelas,
        });
        this.carregando.set(false);
      },
      error: (erro: Error) => {
        this.acrescentar({ autor: 'agente', texto: erro.message, erro: true });
        this.carregando.set(false);
      },
    });
  }

  /** Dois toques para apagar: a conversa não volta, e não há modal no caminho. */
  limpar(): void {
    if (!this.confirmandoLimpeza()) {
      this.confirmandoLimpeza.set(true);
      return;
    }
    this.mensagens.set([]);
    this.confirmandoLimpeza.set(false);
  }

  cancelarLimpeza(): void {
    this.confirmandoLimpeza.set(false);
  }

  exportar(): void {
    void this.impressao.exportar();
  }

  private acrescentar(mensagem: Mensagem): void {
    this.mensagens.update((atuais) => [...atuais, mensagem]);
  }
}
