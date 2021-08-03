import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {FileDetails} from './file_details';

/** File details sidebar route. */
export const FILE_DETAILS_ROUTES: Routes = [
  {
    // TODO: path requires slashes to be encoded (%2F). It'd be
    // nicer to use real slashes in the URL, but Angular's wildcard matching is
    // hard.
    path: 'files/:pathType/:path',
    component: FileDetails,
    outlet: 'drawer',
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(FILE_DETAILS_ROUTES),
  ],
  exports: [RouterModule],
})
export class FileDetailsRoutingModule {
}
