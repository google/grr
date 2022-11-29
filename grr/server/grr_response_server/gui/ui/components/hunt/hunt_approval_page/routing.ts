import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HuntApprovalPage} from './hunt_approval_page';

/**
 * Hunt approval page routes.
 */
export const HUNT_APPROVAL_PAGE_ROUTES: Routes = [
  {
    path: 'hunts/:huntId/users/:requestor/approvals/:approvalId',
    component: HuntApprovalPage,
    data: {
      'legacyLink': '#/users/:requestor/approvals/hunt/:huntId/:approvalId',
    }
  },
];
/**
 * Routing module for the hunt approval page.
 */
@NgModule({
  imports: [
    RouterModule.forChild(HUNT_APPROVAL_PAGE_ROUTES),
  ],
  exports: [RouterModule],
})
export class HuntApprovalPageRoutingModule {
}
