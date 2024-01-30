import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

import {CopyButton} from './copy_button';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ClipboardModule,
    CommonModule,
    MatIconModule,
    // keep-sorted end
  ],
  declarations: [CopyButton],
  exports: [CopyButton],
})
export class CopyButtonModule {}
