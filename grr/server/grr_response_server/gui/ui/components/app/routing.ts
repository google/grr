import {GrrRoute} from '../../lib/routing';
import {AdministrationPage} from '../administration_page/administration_page';
import {Artifact} from '../administration_page/artifact';
import {ArtifactsAdministration} from '../administration_page/artifacts_administration';
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
import {V2Redirect} from './v2_redirect';

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
    title: 'GRR | Client Search',
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
        title: 'GRR | Client > Flows',
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
            title: 'GRR | Client > Scheduled Flow',
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
                title: 'GRR | Client > Flow > Results',
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
                title: 'GRR | Client > Flow > Results',
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
                title: 'GRR | Client > Flow > Configuration',
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
                title: 'GRR | Client > Flow > Debug',
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
        title: 'GRR | Client > History',
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
        title: 'GRR | Client > Approvals',
        children: [
          {
            path: ':approvalId/users/:requestor',
            component: ApprovalRequestLoader,
            title: 'GRR | Client > Approvals > Review',
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
            pagePath: `clients/${REDACTED_CLIENT_ID}/approvals`,
            pageTitle: 'Client > Approvals',
          },
        },
      },
      {
        path: 'files',
        component: FileExplorer,
        title: 'GRR | Client > File Explorer',
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
    title: 'GRR | Fleet Collections',
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
        title: 'GRR | Fleet Collection',
        children: [
          {path: '', redirectTo: 'results', pathMatch: 'full'},
          {
            path: 'results',
            component: FleetCollectionResults,
            title: 'GRR | Fleet Collection > Results',
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
            title: 'GRR | Fleet Collection > Errors',
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
            title: 'GRR | Fleet Collection > Configuration',
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/configuration`,
                pageTitle: 'Fleet Collection > Configuration',
              },
            },
          },
          {
            path: 'debug',
            component: FleetCollectionDebugging,
            title: 'GRR | Fleet Collection > Debug',
            data: {
              'pageViewTracking': {
                pagePath: `fleet-collections/${REDACTED_FLEET_COLLECTION_ID}/debug`,
                pageTitle: 'Fleet Collection > Debug',
              },
            },
          },
          {
            path: 'approvals',
            component: FleetCollectionApprovals,
            title: 'GRR | Fleet Collection > Approvals',
            children: [
              {
                path: ':approvalId/users/:requestor',
                component: FleetCollectionApprovalRequestLoader,
                title: 'GRR | Fleet Collection > Approval > Review',
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
    title: 'GRR | New Fleet Collection',
    data: {
      'pageViewTracking': {
        pagePath: `new-fleet-collection`,
        pageTitle: 'New Fleet Collection',
      },
    },
  },
];

/** Routes and subroutes for the administration page */
export const ADMINISTRATION_ROUTES: GrrRoute[] = [
  {
    path: 'administration',
    component: AdministrationPage,
    title: 'GRR | Administration',
    data: {
      'pageViewTracking': {
        pagePath: `administration`,
        pageTitle: 'Administration',
      },
    },
    children: [
      {
        path: 'artifacts',
        component: ArtifactsAdministration,
        title: 'GRR | Administration > Artifacts',
        data: {
          'pageViewTracking': {
            pagePath: `administration/artifacts`,
            pageTitle: 'Administration > Artifacts',
          },
        },
        children: [
          {
            path: ':artifactName',
            component: Artifact,
            title: 'GRR | Administration > Artifacts > Artifact',
            data: {
              'pageViewTracking': {
                pagePath: `administration/artifacts/:artifactName`,
                pageTitle: 'Administration > Artifacts > Artifact',
              },
            },
          },
        ],
      },
    ],
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
  {
    path: 'v2',
    pathMatch: 'prefix',
    children: [
      {
        path: '**',
        component: V2Redirect,
        data: {
          'pageViewTracking': {
            pagePath: `v2`,
            pageTitle: 'Redirect',
          },
        },
      },
    ],
  },
  ...CLIENT_ROUTES,
  ...FLEET_COLLECTION_ROUTES,
  ...ADMINISTRATION_ROUTES,
  ...APPROVAL_PAGE_ROUTES,
  {
    path: '**',
    component: NotFoundPage,
    title: 'GRR | Not Found',
    data: {
      'pageViewTracking': {
        pagePath: 'not-found',
        pageTitle: 'Not Found',
      },
    },
  },
];
