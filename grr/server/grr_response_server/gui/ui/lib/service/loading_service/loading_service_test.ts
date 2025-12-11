import {TestBed} from '@angular/core/testing';

import {LoadingService} from './loading_service';

describe('LoadingService', () => {
  let loadingService: LoadingService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [],
      providers: [LoadingService],
      teardown: {destroyAfterEach: true},
    }).compileComponents();

    loadingService = TestBed.inject(LoadingService);
  });

  it('sets loading state to `true` when a url is added', () => {
    expect(loadingService.isLoading()).toBeFalse();

    loadingService.updateLoadingUrls('url1', true);
    expect(loadingService.isLoading()).toBeTrue();
  });

  it('sets loading state to `false` when all urls are removed', () => {
    loadingService.updateLoadingUrls('url1', true);
    loadingService.updateLoadingUrls('url2', true);
    expect(loadingService.isLoading()).toBeTrue();

    loadingService.updateLoadingUrls('url1', false);
    expect(loadingService.isLoading()).toBeTrue();

    loadingService.updateLoadingUrls('url2', false);
    expect(loadingService.isLoading()).toBeFalse();
  });
});
