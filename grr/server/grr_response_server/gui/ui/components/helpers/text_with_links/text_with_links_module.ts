import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {TextWithLinks} from './text_with_links';

/**
 * Module for the Linkify component.
 */
@NgModule({
  imports: [
    CommonModule,
  ],
  declarations: [TextWithLinks],
  exports: [TextWithLinks]
})
export class TextWithLinksModule {
}
