import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowListModule} from '@app/components/flow_list/module';
import {FlowListEntry} from '@app/lib/models/flow';
import {newFlowDescriptorMap, newFlowListEntry} from '@app/lib/models/model_test_util';
import {ClientFacade} from '@app/store/client_facade';
import {FlowFacade} from '@app/store/flow_facade';
import {FlowFacadeMock, mockFlowFacade} from '@app/store/flow_facade_test_util';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';
import {FlowList} from './flow_list';




initTestEnvironment();

describe('FlowList Component', () => {
  let flowListEntries$: Subject<ReadonlyArray<FlowListEntry>>;
  let flowFacade: FlowFacadeMock;
  let clientFacade: Partial<ClientFacade>;

  beforeEach(async(() => {
    flowListEntries$ = new Subject();
    flowFacade = mockFlowFacade();
    clientFacade = {flowListEntries$};

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowListModule,
          ],

          providers: [
            {provide: FlowFacade, useValue: flowFacade},
            {provide: ClientFacade, useValue: clientFacade},
          ]
        })
        .compileComponents();
  }));

  it('loads and displays Flows', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    flowFacade.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
        },
        {
          name: 'KeepAlive',
          friendlyName: 'KeepAlive',
        }));
    flowListEntries$.next([
      newFlowListEntry({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlowListEntry({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Side File Finder');
    expect(text).toContain('morty');
    expect(text).toContain('KeepAlive');
    expect(text).toContain('rick');
  });

  it('loads and displays Flows with missing FlowDescriptors', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    // Flows won't be displayed until descriptors are fetched.
    flowFacade.flowDescriptorsSubject.next(newFlowDescriptorMap());

    flowListEntries$.next([
      newFlowListEntry({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlowListEntry({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('ClientFileFinder');
    expect(text).toContain('KeepAlive');
  });
});
