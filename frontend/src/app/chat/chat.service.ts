import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { Base, RespostaChat } from './modelos';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);

  perguntar(pergunta: string): Observable<RespostaChat> {
    return this.http
      .post<RespostaChat>('/api/chat', { pergunta })
      .pipe(catchError((erro) => throwError(() => new Error(this.mensagemDe(erro)))));
  }

  base(): Observable<Base> {
    return this.http.get<Base>('/api/base');
  }

  /** O backend manda instrucoes acionaveis em `detail`; preserva-las importa. */
  private mensagemDe(erro: HttpErrorResponse): string {
    const detalhe = erro.error?.detail;
    if (typeof detalhe === 'string') {
      return detalhe;
    }
    if (erro.status === 0) {
      return 'Nao foi possivel falar com o servidor. Ele esta no ar?';
    }
    return 'Algo deu errado ao processar a pergunta. Tente novamente.';
  }
}
