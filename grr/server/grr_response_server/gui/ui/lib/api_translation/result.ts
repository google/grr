import {ApiHuntResult, ClientSummary} from '../api/api_interfaces';
import {CellComponent, CellData, PayloadTranslation} from '../models/result';

import {createOptionalDate} from './primitive';

/** HUNT_RESULT_COLUMNS describes how to render HuntResultRow. */
export const HUNT_RESULT_COLUMNS = {
  'clientId': {title: 'Client ID'},
  'collectedAt': {title: 'Collected At', component: CellComponent.TIMESTAMP},
  'payloadType': {title: 'Result Type'},
} as const;

/** Constructs a HuntResultsRow from an ApiHuntResult. */
export function toHuntResultRow(hr: ApiHuntResult):
    CellData<typeof HUNT_RESULT_COLUMNS> {
  return {
    'clientId': hr.clientId,
    'payloadType': hr.payloadType,
    'collectedAt': createOptionalDate(hr.timestamp),
  };
}

/** CLIENT_COLUMNS describes how to render ClientRow. */
export const CLIENT_COLUMNS = {
  'fqdn': {title: 'FQDN'},
  'userNum': {title: 'User #'},
  'usernames': {title: 'Usernames'},
} as const;

/** Constructs a ClientRow from a ClientSummary. */
export function toClienRow(cs: ClientSummary): CellData<typeof CLIENT_COLUMNS> {
  return {
    'fqdn': cs?.systemInfo?.fqdn,
    'userNum': cs?.users?.length,
    'usernames': cs?.users?.map(u => u.username).join(', ') ?? '',
  };
}

/** Maps PayloadType to corresponding translation information. */
export const PAYLOAD_TYPE_TRANSLATION = {
  'ApiHuntResult': {
    tabName: 'N/A',
    translateFn: toHuntResultRow,
    columns: HUNT_RESULT_COLUMNS
  } as PayloadTranslation<typeof HUNT_RESULT_COLUMNS>,
  'ClientSummary': {
    tabName: 'Client Summary',
    translateFn: toClienRow,
    columns: CLIENT_COLUMNS,
  } as PayloadTranslation<typeof CLIENT_COLUMNS>,
} as const;