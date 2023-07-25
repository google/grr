import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {GrrRoute} from '../../lib/routing';
import {ApprovalPage} from '../approval_page/approval_page';
import {ClientDetails} from '../client_details/client_details';
import {ClientPage} from '../client_page/client_page';
import {FlowSection} from '../client_page/flow_section';
import {VfsSection} from '../client_page/vfs_section';
import {ClientSearch} from '../client_search/client_search';
import {HexView} from '../data_renderers/hex_view/hex_view';
import {StatView} from '../data_renderers/stat_view/stat_view';
import {TextView} from '../data_renderers/text_view/text_view';
import {FileDetailsPage} from '../file_details/file_details_page';
import {Home} from '../home/home';
import {HuntApprovalPage} from '../hunt/hunt_approval_page/hunt_approval_page';
import {HuntHelp} from '../hunt/hunt_help/hunt_help';
import {HuntOverviewPage} from '../hunt/hunt_overview_page/hunt_overview_page';
import {HuntPage} from '../hunt/hunt_page/hunt_page';
import {HuntResultDetails} from '../hunt/hunt_page/hunt_result_details/hunt_result_details';
import {ModifyHunt} from '../hunt/modify_hunt/modify_hunt';
import {NewHunt} from '../hunt/new_hunt/new_hunt';

import {NotFoundPage} from './not_found_page';


const REDACTED_CLIENT_ID = 'client_id';
const REDACTED_FLOW_ID = 'flow_id';
const REDACTED_HUNT_ID = 'hunt_id';
const REDACTED_APPROVAL_ID = 'approval_id';
const REDACTED_USER = 'user';
const REDACTED_FILE_PATH = 'file_path';
const REDACTED_PATH_TYPE = 'path_type';
const REDACTED_RESULT_KEY = 'result_key';
const REDACTED_PAYLOAD_TYPE = 'payload_type';


/** Routes and subroutes for the client page */
export const CLIENT_ROUTES: GrrRoute[] = [
  {
    path: 'clients',
    component: ClientSearch,
    data: {
      legacyLink: '#/search?q=:q',
      pageViewTracking: {
        pagePath: 'client_search',
        pageTitle: 'Client Search',
      }
    }
  },
  {
    path: 'clients/:id',
    component: ClientPage,
    data: {
      legacyLink: '#/clients/:id',
      pageViewTracking: {
        pagePath: `clients/${REDACTED_CLIENT_ID}`,
        pageTitle: 'Client > Flows',
      }
    },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'flows',
      },
      // A trailing slash breaks navigation when the URL contains an
      // auxiliary route upon page load. E.g. refreshing the browser on
      // `/clients/x/flows/(drawer:details)` is not routed correctly - Angular
      // shows the error page. One hypothesis is that Angular assumes that
      // the auxiliary route should belong to `/flows/` and not the root `/`.
      // We fix this by preventing the trailing slash and redirecting
      // `/flows/` to `/flows`.
      {path: 'flows/', pathMatch: 'full', redirectTo: 'flows'},
      {
        path: 'flows',
        component: FlowSection,
        data: {
          legacyLink: '#/clients/:id/flows/',
          // Reuse `FlowSection` component when switching between `/flows` and
          // `/flows/:id` to preserve UI state, e.g. open panels.
          reuseComponent: true,
        },
      },
      {
        path: 'flows/:flowId',
        component: FlowSection,
        data: {
          legacyLink: '#/clients/:id/flows/:flowId',
          reuseComponent: true,
          pageViewTracking: {
            path: `flows/${REDACTED_FLOW_ID}`,
            pageTitle: 'Client > Flow',
          }
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
          legacyLink: '#/clients/:id/vfs/fs/os:path',
          collapseClientHeader: true,
          pageViewTracking: {
            path: `files/${REDACTED_FILE_PATH}`,
            pageTitle: 'Client > Browse Files',
          }
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
  {
    // TODO: `path` requires slashes to be encoded (`%2F`). It'd be
    // nicer to use real slashes in the URL, but Angular's wildcard matching
    // is hard.
    path: 'files/:pathType/:path',
    component: FileDetailsPage,
    outlet: 'drawer',
    children: [
      {path: '', redirectTo: 'stat', pathMatch: 'full'},
      {
        path: 'stat',
        component: StatView,
        data: {
          pageViewTracking: {
            pagePath: `files/${REDACTED_PATH_TYPE}/${REDACTED_FILE_PATH}`,
            pageTitle: 'Client > Browse Files > Stat',
          },
        }
      },
      {
        path: 'text',
        component: TextView,
        data: {
          pageViewTracking: {
            pagePath: `files/${REDACTED_PATH_TYPE}/${REDACTED_FILE_PATH}`,
            pageTitle: 'Client > Browse Files > Text',
          }
        },
      },
      {
        path: 'blob',
        component: HexView,
        data: {
          pageViewTracking: {
            pagePath: `files/${REDACTED_PATH_TYPE}/${REDACTED_FILE_PATH}`,
            pageTitle: 'Client > Browse Files > Blob',
          }
        },
      },
    ],
    data: {
      pageViewTracking: {
        pagePath: `files/${REDACTED_PATH_TYPE}/${REDACTED_FILE_PATH}`,
        pageTitle: 'Client > Browse Files',
      }
    }
  },
  {
    path: 'details/:clientId',
    component: ClientDetails,
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath: `details/${REDACTED_CLIENT_ID}`,
        pageTitle: 'Client > Client Details',
      }
    }
  },
  {
    path: 'details/:clientId/:sourceFlowId',
    component: ClientDetails,
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath: `details/${REDACTED_CLIENT_ID}/${REDACTED_FLOW_ID}`,
        pageTitle: 'Client > Client Details',
      }
    }
  },
];

/** Routes and subroutes for the hunt page */
export const HUNT_ROUTES: GrrRoute[] = [
  {
    path: 'hunts',
    pathMatch: 'full',
    component: HuntOverviewPage,
    data: {
      legacyLink: '#/hunts',
      pageViewTracking: {
        pagePath: `hunts`,
        pageTitle: 'Hunt Overview',
      },
    }
  },
  {
    path: 'hunts/:id',
    component: HuntPage,
    data: {
      legacyLink: '#/hunts/:id',
      pageViewTracking: {
        pagePath: `hunts/${REDACTED_HUNT_ID}`,
        pageTitle: 'Hunt Details',
      },
    }
  },
  {
    path: 'new-hunt',
    component: NewHunt,
    data: {
      pageViewTracking: {
        pagePath: `new_hunt`,
        pageTitle: 'New Hunt',
      },
    },
  },
  {
    path: 'modify-hunt',
    component: ModifyHunt,
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath: `modify_hunt`,
        pageTitle: 'Hunt Details > Modify Hunt',
      },
    },
  },
  {
    path: 'help',
    component: HuntHelp,
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath: `hunts/help`,
        pageTitle: 'Hunt Overview > Help',
      },
    },
  },
  {
    path: 'result-details/:key',
    redirectTo: 'result-details/:key/',
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath: `result-details/${REDACTED_RESULT_KEY}`,
        pageTitle: 'Hunt Details > View Result',
      },
    },
  },
  {
    path: 'result-details/:key/:payloadType',
    component: HuntResultDetails,
    outlet: 'drawer',
    data: {
      pageViewTracking: {
        pagePath:
            `result-details/${REDACTED_RESULT_KEY}/${REDACTED_PAYLOAD_TYPE}`,
        pageTitle: 'Hunt Details > View Result',
      },
    },
  },
];

/** Routes and subroutes for approval pages */
export const APPROVAL_PAGE_ROUTES: GrrRoute[] = [
  {
    path: 'clients/:clientId/users/:requestor/approvals/:approvalId',
    component: ApprovalPage,
    data: {
      legacyLink: '#/users/:requestor/approvals/client/:clientId/:approvalId',
      pageViewTracking: {
        pagePath: `clients/${REDACTED_CLIENT_ID}/users/${
            REDACTED_USER}/approvals/${REDACTED_APPROVAL_ID}`,
        pageTitle: 'Client Approval',
      },
    }
  },
  {
    path: 'hunts/:huntId/users/:requestor/approvals/:approvalId',
    component: HuntApprovalPage,
    data: {
      legacyLink: '#/users/:requestor/approvals/hunt/:huntId/:approvalId',
      pageViewTracking: {
        pagePath: `hunts/${REDACTED_HUNT_ID}/users/${REDACTED_USER}/approvals/${
            REDACTED_APPROVAL_ID}`,
        pageTitle: 'Hunt Approval',
      },
    }
  },
];

const APP_ROUTES: GrrRoute[] = [
  {
    path: '',
    component: Home,
    data: {
      pageViewTracking: {
        pagePath: `/`,
        pageTitle: 'Home',
      },
    }
  },
  ...CLIENT_ROUTES,
  ...HUNT_ROUTES,
  ...APPROVAL_PAGE_ROUTES,
  {
    path: '**',
    component: NotFoundPage,
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(APP_ROUTES),
  ],
  exports: [
    RouterModule,
  ]
})
export class AppRoutingModule {
}
