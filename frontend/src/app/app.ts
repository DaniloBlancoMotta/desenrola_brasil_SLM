import { ChangeDetectionStrategy, Component } from '@angular/core';

import { Chat } from './chat/chat';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Chat],
  template: `<app-chat />`,
})
export class App {}
