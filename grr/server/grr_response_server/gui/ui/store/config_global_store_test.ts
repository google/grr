import {TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';

import * as api from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';

initTestEnvironment();

describe('ConfigGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let configGlobalStore: ConfigGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        ConfigGlobalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false}
    });

    configGlobalStore = TestBed.inject(ConfigGlobalStore);
  });

  it('calls the API on subscription to flowDescriptors$', () => {
    configGlobalStore.flowDescriptors$.subscribe();
    expect(httpApiService.listFlowDescriptors).toHaveBeenCalled();
  });

  it('correctly emits the API results in flowDescriptors$', (done) => {
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

    configGlobalStore.flowDescriptors$.subscribe((results) => {
      expect(results).toEqual(expected);
      done();
    });

    httpApiService.mockedObservables.listFlowDescriptors.next([
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
  });

  it('calls the API on subscription to artifactDescriptors$', () => {
    configGlobalStore.artifactDescriptors$.subscribe();
    expect(httpApiService.listArtifactDescriptors).toHaveBeenCalled();
  });

  it('correctly emits the API results in artifactDescriptors$', (done) => {
    configGlobalStore.artifactDescriptors$.subscribe((results) => {
      expect(results.get('TestArtifact')).toEqual(jasmine.objectContaining({
        name: 'TestArtifact'
      }));
      done();
    });

    httpApiService.mockedObservables.listArtifactDescriptors.next([
      {
        artifact: {
          name: 'TestArtifact',
        },
      },
    ]);
  });

  it('calls the API on subscription to outputPluginDescriptors$', () => {
    configGlobalStore.outputPluginDescriptors$.subscribe();
    expect(httpApiService.listOutputPluginDescriptors).toHaveBeenCalled();
  });

  it('correctly emits the API results in outputPluginDescriptors$', (done) => {
    configGlobalStore.outputPluginDescriptors$.subscribe((results) => {
      expect(results.get('TestOutputPlugin')).toEqual(jasmine.objectContaining({
        name: 'TestOutputPlugin'
      }));
      done();
    });

    httpApiService.mockedObservables.listOutputPluginDescriptors.next([
      {
        name: 'TestOutputPlugin',
      },
    ]);
  });

  it('calls the API on subscription to uiConfig$', () => {
    expect(httpApiService.fetchUiConfig).not.toHaveBeenCalled();
    configGlobalStore.uiConfig$.subscribe();
    expect(httpApiService.fetchUiConfig).toHaveBeenCalled();
  });

  it('correctly emits the API results in uiConfig$', (done) => {
    const expected: api.ApiUiConfig = {
      profileImageUrl: 'https://foo',
    };

    configGlobalStore.uiConfig$.subscribe((results) => {
      expect(results).toEqual(expected);
      done();
    });

    httpApiService.mockedObservables.fetchUiConfig.next({
      profileImageUrl: 'https://foo',
    });
  });

  it('calls the API on subscription to clientsLabels$', () => {
    configGlobalStore.clientsLabels$.subscribe();
    expect(httpApiService.fetchAllClientsLabels).toHaveBeenCalled();
  });

  it('correctly emits the translated API results in clientLabels$', (done) => {
    const expected = [
      'first_label',
      'second_label',
    ];

    configGlobalStore.clientsLabels$.subscribe((results) => {
      expect(results).toEqual(expected);
      done();
    });

    httpApiService.mockedObservables.fetchAllClientsLabels.next([
      {
        owner: 'first_owner',
        name: 'first_label',
      },
      {
        owner: 'second_owner',
        name: 'second_label',
      },
    ]);
  });

  it('calls the API on subscription to binaries$', () => {
    expect(httpApiService.listBinaries).not.toHaveBeenCalled();
    configGlobalStore.binaries$.subscribe();
    expect(httpApiService.listBinaries).toHaveBeenCalled();
  });

  it('correctly emits the API results in binaries$', async () => {
    const promise = firstValueFrom(configGlobalStore.binaries$);

    httpApiService.mockedObservables.listBinaries.next({
      items: [
        {
          type: api.ApiGrrBinaryType.PYTHON_HACK,
          path: 'windows/test/hello.py',
          size: '1',
          timestamp: '1',
          hasValidSignature: true
        },
      ]
    });

    expect(await promise).toEqual([jasmine.objectContaining({
      path: 'windows/test/hello.py',
    })]);
  });
});
