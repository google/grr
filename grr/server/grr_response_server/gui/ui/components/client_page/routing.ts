import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {RoutesWithCustomData} from '../../lib/routing';
import {HexView} from '../data_renderers/hex_view/hex_view';
import {StatView} from '../data_renderers/stat_view/stat_view';
import {TextView} from '../data_renderers/text_view/text_view';

import {ClientPage} from './client_page';
import {FlowSection} from './flow_section';
import {VfsSection} from './vfs_section';

/** Route data that indicates to collapse the client header. */
export interface CollapseClientHeader {
  collapseClientHeader?: boolean;
}

/**
 * Client details page route.
 */
export const CLIENT_PAGE_ROUTES: RoutesWithCustomData = [
  {
    path: 'clients/:id',
    component: ClientPage,
    data: {'legacyLink': '#/clients/:id'},
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'flows',
      },
      // A trailing slash breaks navigation when the URL contains an
      // auxiliary route upon page load. E.g. refreshing the browser on
      // /clients/x/flows/(drawer:details) is not routed correctly - Angular
      // shows the error page. One hypothesis is that Angular assumes that
      // the auxiliary route should belong to /flows/ and not the root /.
      // We fix this by preventing the trailing slash and redirecting
      // /flows/ to /flows.
      {path: 'flows/', pathMatch: 'full', redirectTo: 'flows'},
      {
        path: 'flows',
        component: FlowSection,
        data: {
          'legacyLink': '#/clients/:id/flows/',
          // Reuse FlowSection component when switching between /flows and
          // /flows/:id to preserve UI state, e.g. open panels.
          'reuseComponent': true
        },
      },
      {
        path: 'flows/:flowId',
        component: FlowSection,
        data: {
          'legacyLink': '#/clients/:id/flows/:flowId',
          'reuseComponent': true
        },
      },
      {
        path: 'files',
        // Redirect to the URL-encoded root path `/` => `%2F`.
        // TODO: Use pretty URLs instead of URL-encoded paths.
        redirectTo: 'files/%2F',
      },
      {
        // TODO: Use pretty URLs instead of URL-encoded paths.
        path: 'files/:path',
        component: VfsSection,
        data: {
          'legacyLink': '#/clients/:id/vfs/fs/os:path',
          'collapseClientHeader': true,
        },
        children: [
          {path: '', redirectTo: 'stat', pathMatch: 'full'},
          {path: 'stat', component: StatView},
          {path: 'text', component: TextView},
          {path: 'blob', component: HexView},
        ]
      },
    ]
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_PAGE_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientPageRoutingModule {
}
