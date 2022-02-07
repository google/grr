import {NgModule} from '@angular/core';

import {HuntPage} from './hunt_page';
import {HuntPageRoutingModule} from './routing';

/**
 * Module for hunt view page.
 */
@NgModule({
  imports: [HuntPageRoutingModule],
  declarations: [HuntPage],
})
export class HuntPageModule {
}
