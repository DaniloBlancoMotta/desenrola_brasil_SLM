import { provideZonelessChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { bootstrapApplication } from '@angular/platform-browser';

import { App } from './app/app';

bootstrapApplication(App, {
  providers: [provideZonelessChangeDetection(), provideHttpClient()],
}).catch((erro) => console.error(erro));
