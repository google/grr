import {ApiClient} from '@app/lib/api/api_interfaces';
import {Client} from '@app/lib/models/client';

import {initTestEnvironment} from '../../testing';

import {translateClient} from './client';


initTestEnvironment();

describe('Client API Translation', () => {
  it('converts all client fields correctly', () => {
    const apiClient: ApiClient = {
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.bar',
        os: 'Linux',
      },
      firstSeenAt: '1571789996678000',
      lastSeenAt: '1571789996679000',
      lastBootedAt: '1571789996680000',
      lastClock: '1571789996681000',
      labels: [
        {name: 'a', owner: 'ao'},
        {name: 'b', owner: 'bo'},
      ],
    };
    const client: Client = {
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.bar',
        os: 'Linux',
      },
      firstSeenAt: new Date(1571789996678),
      lastSeenAt: new Date(1571789996679),
      lastBootedAt: new Date(1571789996680),
      lastClock: new Date(1571789996681),
      labels: [
        {name: 'a', owner: 'ao'},
        {name: 'b', owner: 'bo'},
      ],
    };
    expect(translateClient(apiClient)).toEqual(client);
  });

  it('converts optional client fields correctly', () => {
    const apiClient: ApiClient = {
      clientId: 'C.1234',
      labels: [],
    };
    const client: Client = {
      clientId: 'C.1234',
      fleetspeakEnabled: false,
      knowledgeBase: {
        fqdn: undefined,
        os: undefined,
      },
      firstSeenAt: undefined,
      lastSeenAt: undefined,
      lastBootedAt: undefined,
      lastClock: undefined,
      labels: [],
    };
    expect(client).toEqual(translateClient(apiClient));
  });
});
