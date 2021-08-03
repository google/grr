import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {DrawerLink, DrawerRouterLinkWithHref} from './drawer_link';

/**
 * Module for the ScheduledFlowList component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
  ],
  declarations: [
    DrawerLink,
    DrawerRouterLinkWithHref,
  ],
  exports: [
    DrawerLink,
    DrawerRouterLinkWithHref,
  ],
})
export class DrawerLinkModule {
}
