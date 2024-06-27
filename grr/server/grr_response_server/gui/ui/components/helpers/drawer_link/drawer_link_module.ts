import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {DrawerLink, DrawerRouterLink} from './drawer_link';

/**
 * Module for the ScheduledFlowList component.
 */
@NgModule({
  imports: [CommonModule, RouterModule],
  declarations: [DrawerLink, DrawerRouterLink],
  exports: [DrawerLink, DrawerRouterLink],
})
export class DrawerLinkModule {}
