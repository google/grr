import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {SubmitOnMetaEnterDirective} from './submit_on_meta_enter_directive';

@NgModule({
  imports: [CommonModule],
  declarations: [SubmitOnMetaEnterDirective],
  exports: [SubmitOnMetaEnterDirective]
})
export class SubmitOnMetaEnterModule {
}
