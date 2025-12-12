import {TestBed} from '@angular/core/testing';
import {BrowserModule} from '@angular/platform-browser';

import {FlowType} from '../../lib/models/flow';
import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {FriendlyFlowNamePipe} from './friendly_flow_name';

describe('Friendly Flow Name Pipe', () => {
  let globalStoreMock: GlobalStoreMock;
  let pipe: FriendlyFlowNamePipe;

  beforeEach(() => {
    globalStoreMock = newGlobalStoreMock();
    TestBed.configureTestingModule({
      imports: [BrowserModule],
      providers: [
        FriendlyFlowNamePipe,
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();

    pipe = TestBed.inject(FriendlyFlowNamePipe);
  });

  it('returns the flow item name if name is a FlowType', () => {
    expect(pipe.transform(FlowType.COLLECT_FILES_BY_KNOWN_PATH)).toEqual(
      'Collect files from exact paths',
    );
  });

  it('returns unknown flow title if flow name is not set', () => {
    expect(pipe.transform(undefined)).toEqual('Unknown flow');
  });
});
