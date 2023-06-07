import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {MatDrawer} from '@angular/material/sidenav';
import {ActivatedRoute, ActivatedRouteSnapshot, ActivationEnd, NavigationStart, Router} from '@angular/router';
import {distinctUntilChanged, filter, map, startWith} from 'rxjs/operators';
import {safeLocation} from 'safevalues/dom';

import {makeLegacyLink, makeLegacyLinkFromRoute} from '../../lib/routing';
import {MetricsService, UiRedirectDirection, UiRedirectSource} from '../../lib/service/metrics_service/metrics_service';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

const CLIENTS_ROUTE = '/clients';

/** Recursively searches a route and all child routes to fulfill a predicate. */
function findRouteWith(
    route: ActivatedRouteSnapshot,
    pred: ((route: ActivatedRouteSnapshot) => boolean)): ActivatedRouteSnapshot|
    undefined {
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

function hasLegacyLink(route: ActivatedRouteSnapshot) {
  return route.data['legacyLink'] !== undefined;
}

/**
 * The root component.
 */
@Component({
  selector: 'app-root',
  templateUrl: './app.ng.html',
  styleUrls: ['./app.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [MetricsService],
})
export class App {
  private readonly navigationEndEvent$ = this.router.events.pipe(filter(
      (event): event is ActivationEnd => event instanceof ActivationEnd));

  readonly fallbackLink$ = this.navigationEndEvent$.pipe(
      map(event => {
        const route = event.snapshot;
        const routeWithLegacyLink = findRouteWith(route, hasLegacyLink);
        if (routeWithLegacyLink === undefined) {
          return makeLegacyLink();
        } else {
          return makeLegacyLinkFromRoute(routeWithLegacyLink);
        }
      }),
  );

  registerRedirect() {
    this.metricsService.registerUIRedirect(
        UiRedirectDirection.NEW_TO_OLD, UiRedirectSource.REDIRECT_BUTTON);
  }

  readonly isClientsPath$ = this.navigationEndEvent$.pipe(
      map(() => this.router.url.startsWith((CLIENTS_ROUTE))),
      distinctUntilChanged(),
  );

  @ViewChild('drawer') drawer!: MatDrawer;

  readonly uiConfig$ = this.configGlobalStore.uiConfig$;

  readonly heading$ = this.configGlobalStore.uiConfig$.pipe(
      map(config => config.heading),
  );

  readonly canaryMode$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.canaryMode),
      startWith(false),
  );

  constructor(
      private readonly router: Router,
      private readonly activatedRoute: ActivatedRoute,
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly metricsService: MetricsService,
  ) {
    this.navigationEndEvent$.subscribe(async (event) => {
      const drawerRoute =
          findRouteWith(event.snapshot, (route) => route.outlet === 'drawer');
      if (drawerRoute) {
        await this.drawer.open();
      } else {
        await this.drawer.close();
      }
    });

    // Redirect URLs with fragments (#) to legacy UI.
    this.router.events
        .pipe(filter(
            (event): event is NavigationStart =>
                event instanceof NavigationStart))
        .subscribe((event) => {
          const url: string = event?.url;
          if (!url) return;

          const i = url.indexOf('#');
          if (i < 0) return;  // has no fragment

          this.metricsService.registerUIRedirect(
              UiRedirectDirection.NEW_TO_OLD, UiRedirectSource.REDIRECT_ROUTER);
          const fragmentWithHashtag = url.substring(i);
          safeLocation.setHref(
              window.location, makeLegacyLink(fragmentWithHashtag));
        });

    this.activatedRoute.queryParamMap
        .pipe(
            map(params => {
              if (!params.has('source')) return;

              const source = params.get('source') as UiRedirectSource;
              this.metricsService.registerUIRedirect(
                  UiRedirectDirection.OLD_TO_NEW, source);

              // Remove query params without reloading the page.
              this.router.navigate([], {
                queryParams: {
                  'source': null,
                },
                queryParamsHandling: 'merge'
              });
            }),
            )
        .subscribe();
  }

  ngAfterViewInit() {
    this.drawer.closedStart.subscribe(() => {
      this.router.navigate([{outlets: {'drawer': null}}], {replaceUrl: true});
    });
  }
}
