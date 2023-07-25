import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

import {CopyButton} from './copy_button';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    ClipboardModule,
    CommonModule,
    MatIconModule,
    // keep-sorted end
    // clang-format on
  ],
  declarations: [CopyButton],
  exports: [CopyButton]
})
export class CopyButtonModule {
}
