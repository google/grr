import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HexView} from '../data_renderers/hex_view/hex_view';
import {StatView} from '../data_renderers/stat_view/stat_view';
import {TextView} from '../data_renderers/text_view/text_view';

import {FileDetailsPage} from './file_details_page';

/** File details sidebar route. */
export const FILE_DETAILS_ROUTES: Routes = [
  {
    // TODO: path requires slashes to be encoded (%2F). It'd be
    // nicer to use real slashes in the URL, but Angular's wildcard matching is
    // hard.
    path: 'files/:pathType/:path',
    component: FileDetailsPage,
    outlet: 'drawer',
    children: [
      {path: '', redirectTo: 'stat', pathMatch: 'full'},
      {path: 'stat', component: StatView},
      {path: 'text', component: TextView},
      {path: 'blob', component: HexView},
    ]
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
