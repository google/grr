import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

import {CopyButton} from './copy_button';

@NgModule({
  imports: [
    CommonModule,
    ClipboardModule,
    MatIconModule,
  ],
  declarations: [CopyButton],
  exports: [CopyButton]
})
export class CopyButtonModule {
}
