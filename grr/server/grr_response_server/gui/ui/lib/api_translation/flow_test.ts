import {ApiFlow} from '@app/lib/api/api_interfaces';
import {Flow} from '@app/lib/models/flow';
import {initTestEnvironment} from '../../testing';
import {translateFlow} from './flow';


initTestEnvironment();

describe('Flow API Translation', () => {
  it('converts populated ApiFlow correctly', () => {
    const apiFlow: ApiFlow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'KeepAlive',
      creator: 'morty',
      lastActiveAt: '1571789996681000',  // 2019-10-23T00:19:56.681Z
      startedAt: '1571789996679000',     // 2019-10-23T00:19:56.679Z
    };

    const flow: Flow = {
      flowId: '1234',
      clientId: 'C.4567',
      name: 'KeepAlive',
      creator: 'morty',
      lastActiveAt: new Date(1571789996681),
      startedAt: new Date(1571789996679),
      args: undefined,
      progress: undefined,
    };

    expect(translateFlow(apiFlow)).toEqual(flow);
  });
});
