import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {ApprovalPage} from './approval_page';


/** Approval page route. */
export const APPROVAL_ROUTES: Routes = [
  {
    path: 'clients/:clientId/users/:requestor/approvals/:approvalId',
    component: ApprovalPage
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
