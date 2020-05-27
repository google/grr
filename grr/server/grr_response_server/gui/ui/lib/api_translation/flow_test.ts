import {ApiFlow, ApiFlowResult, ApiFlowState} from '@app/lib/api/api_interfaces';
import {newPathSpec} from '@app/lib/api/api_test_util';
import {Flow, FlowResult, FlowState} from '@app/lib/models/flow';
import {initTestEnvironment} from '../../testing';
import {translateFlow, translateFlowResult} from './flow';



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
      state: ApiFlowState.TERMINATED,
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
      state: FlowState.FINISHED,
    };

    expect(translateFlow(apiFlow)).toEqual(flow);
  });
});

describe('ApiFlowResult translation', () => {
  it('converts ApiFlowResult to FlowResult correctly', () => {
    const apiFlowResult: ApiFlowResult = {
      payload: {
        '@type': 'StatEntry',
        path: newPathSpec('/foo/bar'),
      },
      payloadType: 'StatEntry',
      timestamp: '1571789996681000',  // 2019-10-23T00:19:56.681Z
      tag: 'someTag'
    };

    const flowResult: FlowResult = {
      payload: {
        path: newPathSpec('/foo/bar'),
      },
      tag: 'someTag',
      timestamp: new Date(1571789996681),
    };

    expect(translateFlowResult(apiFlowResult)).toEqual(flowResult);
  });
});
