import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule, MatIconRegistry} from '@angular/material/icon';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatTabsModule} from '@angular/material/tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {ActivationEnd, Router, RouterModule} from '@angular/router';
import {filter} from 'rxjs/operators';

import {ApiModule} from '../../lib/api/module';
import {GrrActivatedRouteSnapshot} from '../../lib/routing';
import {LoadingService} from '../../lib/service/loading_service/loading_service';
import {GlobalStore} from '../../store/global_store';
import {UserMenu} from './user_menu';

const NEW_FLEET_COLLECTION_ROUTE = '/new-fleet-collection';

/** Recursively searches a route and all child routes to fulfill a predicate. */
function findRouteWith(
  route: GrrActivatedRouteSnapshot,
  pred: (route: GrrActivatedRouteSnapshot) => boolean,
): GrrActivatedRouteSnapshot | undefined {
  for (const child of route.children) {
    const result = findRouteWith(child, pred);
    if (result !== undefined) {
      return result;
    }
  }
  if (pred(route)) {
    return route;
  }
  return undefined;
}

function hasPageViewTracking(route: GrrActivatedRouteSnapshot): boolean {
  return route.data.pageViewTracking !== undefined;
}

/**
 * The root component.
 */
@Component({
  selector: 'app-root',
  templateUrl: './app.ng.html',
  styleUrls: ['./app.scss'],
  imports: [
    ApiModule,
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSidenavModule,
    MatSnackBarModule,
    MatTabsModule,
    MatToolbarModule,
    MatTooltipModule,
    RouterModule,
    UserMenu,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  private readonly router = inject(Router);
  protected readonly globalStore = inject(GlobalStore);
  readonly loadingService = inject(LoadingService);

  private readonly navigationEndEvent$ = this.router.events.pipe(
    filter((event): event is ActivationEnd => event instanceof ActivationEnd),
  );
  private readonly navigationEndEvent = toSignal(this.navigationEndEvent$);

  protected readonly isNewFleetCollectionPath = computed<boolean>(() => {
    if (this.navigationEndEvent() !== undefined) {
      return this.router.url.startsWith(NEW_FLEET_COLLECTION_ROUTE);
    }
    return false;
  });

  constructor() {
    inject(MatIconRegistry).setDefaultFontSetClass('material-icons-outlined');

    this.globalStore.initialize();

    effect(() => {
      const event = this.navigationEndEvent();
      if (!event) return;

      const route = event.snapshot as GrrActivatedRouteSnapshot;
      const routeWithPageViewTracking = findRouteWith(
        route,
        hasPageViewTracking,
      );
      if (routeWithPageViewTracking) {
        // Google Analytics script is inserted in the base html file.
        const gtag = (window as {gtag?: Function}).gtag;
        if (!gtag) return;

        gtag('event', 'page_view', {
          'page_title':
            routeWithPageViewTracking?.data?.pageViewTracking?.pageTitle,
          'page_path':
            routeWithPageViewTracking?.data?.pageViewTracking?.pagePath,
        });
      }
    });
  }
}
