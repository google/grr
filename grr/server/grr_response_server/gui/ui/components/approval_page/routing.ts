import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {RoutesWithLegacyLinks} from '../../lib/routing';

import {ApprovalPage} from './approval_page';


/** Approval page route. */
export const APPROVAL_ROUTES: Routes&RoutesWithLegacyLinks = [
  {
    // @ts-ignore Fix code and remove this comment. Error:
    // TS2322: Type '{ path: string; component: typeof ApprovalPage; data: {
    // legacyLink: string; }; }[]' is not assignable to type 'Routes &
    // RoutesWithLegacyLinks'.
    path: 'clients/:clientId/users/:requestor/approvals/:approvalId',
    component: ApprovalPage,
    data: {
      legacyLink: '#/users/:requestor/approvals/client/:clientId/:approvalId',
    }
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(APPROVAL_ROUTES),
  ],
  exports: [RouterModule],
})
export class ApprovalRoutingModule {
}
