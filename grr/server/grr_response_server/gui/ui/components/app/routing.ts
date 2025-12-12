import {GrrRoute} from '../../lib/routing';
import {ApprovalRequestLoader} from '../client_page/client_approvals/approval_request_loader';
import {ClientApprovals} from '../client_page/client_approvals/client_approvals';
import {ClientFlows} from '../client_page/client_flows/client_flows';
import {FlowConfiguration} from '../client_page/client_flows/flow_configuration';
import {FlowDebugging} from '../client_page/client_flows/flow_debugging';
import {FlowDetails} from '../client_page/client_flows/flow_details';
import {FlowResults} from '../client_page/client_flows/flow_results';
import {ScheduledFlow} from '../client_page/client_flows/scheduled_flow';
import {ClientHistory} from '../client_page/client_history/client_history';
import {ClientHistoryEntry} from '../client_page/client_history/client_history_entry';
import {ClientPage as NewClientPage} from '../client_page/client_page';
import {FileExplorer} from '../client_page/file_explorer/file_explorer';
import {ClientSearch} from '../client_search/client_search';
import {FleetCollectionApprovalRequestLoader} from '../fleet_collections_page/fleet_collection_approvals/fleet_collection_approval_request_loader';
import {FleetCollectionApprovals} from '../fleet_collections_page/fleet_collection_approvals/fleet_collection_approvals';
import {FleetCollectionConfiguration} from '../fleet_collections_page/fleet_collection_configuration/fleet_collection_configuration';
import {FleetCollectionDebugging} from '../fleet_collections_page/fleet_collection_debugging/fleet_collection_debugging';
import {FleetCollectionDetails} from '../fleet_collections_page/fleet_collection_details';
import {FleetCollectionErrors} from '../fleet_collections_page/fleet_collection_errors/fleet_collection_errors';
import {FleetCollectionResults} from '../fleet_collections_page/fleet_collection_results/fleet_collection_results';
import {FleetCollectionsPage} from '../fleet_collections_page/fleet_collections_page';
import {NewFleetCollection} from '../new_fleet_collection_page/new_fleet_collection';
import {NotFoundPage} from '../not_found_page/not_found_page';

const REDACTED_CLIENT_ID = 'client_id';
const REDACTED_FLOW_ID = 'flow_id';
const REDACTED_FLEET_COLLECTION_ID = 'fleet_collection_id';
const REDACTED_APPROVAL_ID = 'approval_id';
const REDACTED_USER = 'user';

/** Routes and subroutes for the client page */
export const CLIENT_ROUTES: GrrRoute[] = [
  {
    path: 'clients',
    component: ClientSearch,
    data: {
      'pageViewTracking': {
        pagePath: 'client_search',
        pageTitle: 'Client Search',
      },
    },
  },
  {
    path: 'clients/:clientId',
    component: NewClientPage,
    data: {
      'pageViewTracking': {
        pagePath: `clients/${REDACTED_CLIENT_ID}`,
        pageTitle: 'Client',
      },
    },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'flows',
      },
      {
        path: 'flows',
        component: ClientFlows,
        data: {
          'pageViewTracking': {
            pagePath: `clients/${REDACTED_CLIENT_ID}/flows`,
            pageTitle: 'Client > Flows',
          },
        },
        children: [
          {
            path: 'scheduled-flow',
            component: ScheduledFlow,
            data: {
              'pageViewTracking': {
                path: `clients/${REDACTED_CLIENT_ID}/scheduled-flow`,
                pageTitle: 'Client > Flow > Scheduled Flow',
              },
            },
          },
          {
            path: ':flowId',
            component: FlowDetails,
            children: [
              {
                path: '',
                redirectTo: 'results',
                pathMatch: 'full',
                data: {
                  'pageViewTracking': {
                    pagePath: `clients/${REDACTED_CLIENT_ID}/flows/${REDACTED_FLOW_ID}/results`,
                    pageTitle: 'Client > Flow > Results',
                  },
                },
              },
              {
                path: 'results',
                component: FlowResults,
                data: {
                  'pageViewTracking': {
                    pagePath: `clients/${REDACTED_CLIENT_ID}/flows/${REDACTED_FLOW_ID}/results`,
                    pageTitle: 'Client > Flow > Results',
                  },
                },
              },
              {
                path: 'configuration',
                component: FlowConfiguration,
                data: {
                  'pageViewTracking': {
                    pagePath: `clients/${REDACTED_CLIENT_ID}/flows/${REDACTED_FLOW_ID}/configuration`,
                    pageTitle: 'Client > Flow > Configuration',
                  },
                },
              },
              {
                path: 'debug',
                component: FlowDebugging,
                data: {
                  'pageViewTracking': {
                    pagePath: `clients/${REDACTED_CLIENT_ID}/flows/${REDACTED_FLOW_ID}/debug`,
                    pageTitle: 'Client > Flow > Debug',
                  },
                },
              },
            ],
          },
        ],
      },
      {
        path: 'history',
        component: ClientHistory,
        children: [
          {
            path: ':historyTimestamp',
            component: ClientHistoryEntry,
          },
        ],
        data: {
          'pageViewTracking': {
            pagePath: `clients/${REDACTED_CLIENT_ID}/history`,
            pageTitle: 'Client > History',
          },
        },
      },
      {
        path: 'approvals',
        component: ClientApprovals,
        children: [
          {
            path: ':approvalId/users/:requestor',
            component: ApprovalRequestLoader,
            data: {
              'pageViewTracking': {
                pagePath: `clients/${REDACTED_CLIENT_ID}/approvals/${REDACTED_APPROVAL_ID}/users/${REDACTED_USER}`,
                pageTitle: 'Client > Approvals > Review',
              },
            },
          },
        ],
        data: {
          'pageViewTracking': {
            pagePath: `clients/${REDACTED_CLIENT_ID}/approvals${REDACTED_USER}`,
            pageTitle: 'Client > Approvals',
          },
        },
      },
      {
        path: 'files',
        component: FileExplorer,
        data: {
          'pageViewTracking': {
            pagePath: `clients/${REDACTED_CLIENT_ID}/files`,
            pageTitle: 'Client > File Explorer',
          },
        },
      },
    ],
  },
];

/** Routes and subroutes for the fleet collections page */
export const FLEET_COLLECTION_ROUTES: GrrRoute[] = [
  {
    path: 'fleet-collections',
    component: FleetCollectionsPage,
    data: {
      'pageViewTracking': {
        pagePath: `fleet-collections`,
        pageTitle: 'Fleet Collections',
      },
    },
    children: [
      {
        path: ':fleetCollectionId',
        component: FleetCollectionDetails,
        children: [
          {path: '', redirectTo: 'results', pathMatch: 'full'},
          {
            path: 'results',
            component: FleetCollectionResults,
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/results`,
                pageTitle: 'Fleet Collection > Results',
              },
            },
          },
          {
            path: 'errors',
            component: FleetCollectionErrors,
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/errors`,
                pageTitle: 'Fleet Collection > Errors',
              },
            },
          },
          {
            path: 'configuration',
            component: FleetCollectionConfiguration,
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/configuration`,
                pageTitle: 'Fleet Collection > Configuration',
              },
            },
          },
          {path: 'debug', component: FleetCollectionDebugging},
          {
            path: 'approvals',
            component: FleetCollectionApprovals,
            children: [
              {
                path: ':approvalId/users/:requestor',
                component: FleetCollectionApprovalRequestLoader,
                data: {
                  'pageViewTracking': {
                    pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/approvals/${REDACTED_APPROVAL_ID}/users/${REDACTED_USER}`,
                    pageTitle: 'Fleet Collection > Approval > Review',
                  },
                },
              },
            ],
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/approvals`,
                pageTitle: 'Fleet Collection > Approvals',
              },
            },
          },
        ],
        data: {
          'pageViewTracking': {
            path: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}`,
            pageTitle: 'Fleet Collection',
          },
        },
      },
    ],
  },
  {
    path: 'new-fleet-collection',
    component: NewFleetCollection,
    data: {
      'pageViewTracking': {
        pagePath: `new-fleet-collection`,
        pageTitle: 'New Fleet Collection',
      },
    },
  },
];

/** Routes and subroutes for approval pages */
export const APPROVAL_PAGE_ROUTES: GrrRoute[] = [
  {
    path: 'hunts/:huntId/users/:requestor/approvals/:approvalId',
    redirectTo:
      'fleet-collections/:huntId/approvals/:approvalId/users/:requestor',
  },
];

/** Routes and subroutes for the app */
export const APP_ROUTES: GrrRoute[] = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'clients',
  },
  ...CLIENT_ROUTES,
  ...FLEET_COLLECTION_ROUTES,
  ...APPROVAL_PAGE_ROUTES,
  {
    path: '**',
    component: NotFoundPage,
    data: {
      'pageViewTracking': {
        pagePath: 'not-found',
        pageTitle: 'Not Found',
      },
    },
  },
];
