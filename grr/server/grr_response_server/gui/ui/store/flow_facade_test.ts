import {TestBed} from '@angular/core/testing';
import {ApiFlowDescriptor} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowFacade} from '@app/store/flow_facade';
import {GrrStoreModule} from '@app/store/store_module';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

initTestEnvironment();

describe('FlowFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let flowFacade: FlowFacade;
  let apiListFlowDescriptors$: Subject<ReadonlyArray<ApiFlowDescriptor>>;

  beforeEach(() => {
    apiListFlowDescriptors$ = new Subject();
    httpApiService = {
      listFlowDescriptors: jasmine.createSpy('listFlowDescriptors')
                               .and.returnValue(apiListFlowDescriptors$),
    };

    TestBed.configureTestingModule({
      imports: [
        GrrStoreModule,
      ],
      providers: [
        FlowFacade,
        {provide: HttpApiService, useValue: httpApiService},
      ],
    });

    flowFacade = TestBed.inject(FlowFacade);
  });

  it('calls the API on listFlowDescriptors', () => {
    flowFacade.listFlowDescriptors();
    expect(httpApiService.listFlowDescriptors).toHaveBeenCalled();
  });

  it('correctly emits the API results in flowDescriptors$', (done) => {
    flowFacade.listFlowDescriptors();

    apiListFlowDescriptors$.next([
      {
        name: 'ClientSideFileFinder',
        friendlyName: 'Get a file',
        category: 'Filesystem',
        defaultArgs: {'@type': 'test-type'}
      },
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type'}
      },
    ]);

    const expected = new Map([
      [
        'ClientSideFileFinder', {
          name: 'ClientSideFileFinder',
          friendlyName: 'Get a file',
          category: 'Filesystem',
          defaultArgs: {},
        }
      ],
      [
        'KeepAlive', {
          name: 'KeepAlive',
          friendlyName: 'KeepAlive',
          category: 'Misc',
          defaultArgs: {},
        }
      ],
    ]);

    flowFacade.flowDescriptors$.subscribe((results) => {
      expect(results).toEqual(expected);
      done();
    });
  });

  it('emits undefined as selectedFlow$ initially', done => {
    flowFacade.selectedFlow$.subscribe(flow => {
      expect(flow).toBeUndefined();
      done();
    });
  });

  it('emits the selected flow in selectedFlow$', done => {
    flowFacade.listFlowDescriptors();
    apiListFlowDescriptors$.next([
      {
        name: 'ClientSideFileFinder',
        friendlyName: 'Get a file',
        category: 'Filesystem',
        defaultArgs: {'@type': 'test-type'}
      },
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type', foo: 1}
      },
    ]);
    flowFacade.selectFlow('KeepAlive');
    flowFacade.selectedFlow$.subscribe(flow => {
      expect(flow!.name).toEqual('KeepAlive');
      expect(flow!.defaultArgs).toEqual({foo: 1});
      done();
    });
  });

  it('emits the supplied args in selectedFlow$', done => {
    flowFacade.listFlowDescriptors();
    apiListFlowDescriptors$.next([
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type', foo: 1}
      },
    ]);
    flowFacade.selectFlow('KeepAlive', {foo: 42});
    flowFacade.selectedFlow$.subscribe(flow => {
      expect(flow!.name).toEqual('KeepAlive');
      expect(flow!.defaultArgs).toEqual({foo: 42});
      done();
    });
  });

  it('fails when selecting unknown flow', () => {
    flowFacade.listFlowDescriptors();
    apiListFlowDescriptors$.next([
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type'}
      },
    ]);

    expect(() => {
      flowFacade.selectFlow('unknown');
    }).toThrow();
  });


  it('emits undefined in selectedFlow$ after unselectFlow()', done => {
    flowFacade.listFlowDescriptors();
    apiListFlowDescriptors$.next([
      {
        name: 'ClientSideFileFinder',
        friendlyName: 'Get a file',
        category: 'Filesystem',
        defaultArgs: {'@type': 'test-type'},
      },
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type'}
      },
    ]);

    flowFacade.selectFlow('KeepAlive');
    flowFacade.unselectFlow();
    flowFacade.selectedFlow$.subscribe(flow => {
      expect(flow).toBeUndefined();
      done();
    });
  });
});
