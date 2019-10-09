import {NgModule} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {HomeModule} from '../home/module';

import {App} from './app';
import {AppRoutingModule} from './routing';

/**
 * The main application module.
 */
@NgModule({
  declarations: [
    App,
  ],
  imports: [
    BrowserAnimationsModule,
    AppRoutingModule,

    // GRR modules.
    HomeModule,
  ],
  providers: [],
  bootstrap: [App]
})
export class AppModule {
}
