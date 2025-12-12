import {computed, Injectable, signal} from '@angular/core';

/**
 * Service to track the api loading state of the application.
 */
@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  /**
   * True if any api requests are currently loading.
   */
  readonly isLoading = computed(() => this.loadingUrls().size > 0);

  /**
   * Set of api urls that are currently loading.
   */
  private readonly loadingUrls = signal<Set<string>>(new Set<string>());

  updateLoadingUrls(url: string, isLoading: boolean): void {
    this.loadingUrls.update((urls) => {
      // Make a copy of the set as it is managed by the signal.
      const copy = new Set(urls);
      if (isLoading) {
        copy.add(url);
      } else {
        copy.delete(url);
      }
      return copy;
    });
  }
}
