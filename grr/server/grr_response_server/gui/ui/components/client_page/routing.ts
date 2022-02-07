import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {RoutesWithLegacyLinks} from '../../lib/routing';
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
export const CLIENT_PAGE_ROUTES: Routes&RoutesWithLegacyLinks = [
  {
    path: 'clients/:id',
    component: ClientPage,
    data: {legacyLink: '#/clients/:id'},
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'flows/',
      },
      {
        path: 'flows',
        // When loading /flows, redirect to /flows/ to trigger the next route,
        // with flowId = ''. Otherwise, when clicking a direct link to a flow,
        // e.g. /flows/123, Angular observes a Route change and replaces the
        // FlowList component with a new FlowList component, effectively
        // scrolling to the top and losing UI state.
        redirectTo: 'flows/',
      },
      {
        path: 'flows/:flowId',
        component: FlowSection,
        data: {legacyLink: '#/clients/:id/flows/:flowId'},
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
          legacyLink: '#/clients/:id/vfs/fs/os:path',
          collapseClientHeader: true,
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
