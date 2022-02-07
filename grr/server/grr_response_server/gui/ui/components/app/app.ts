import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {MatDrawer} from '@angular/material/sidenav';
import {ActivatedRouteSnapshot, ActivationEnd, Router} from '@angular/router';
import {filter, map, startWith} from 'rxjs/operators';

import {makeLegacyLink, makeLegacyLinkFromRoute} from '../../lib/routing';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

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
})
export class App {
  readonly fallbackLink$ = this.router.events.pipe(
      filter((event): event is ActivationEnd => event instanceof ActivationEnd),
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
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
  ) {
    this.router.events
        .pipe(
            filter(
                (event): event is ActivationEnd =>
                    event instanceof ActivationEnd),
            )
        .subscribe(async (event) => {
          const drawerRoute = findRouteWith(
              event.snapshot, (route) => route.outlet === 'drawer');
          if (drawerRoute) {
            await this.drawer.open();
          } else {
            await this.drawer.close();
          }
        });
  }

  ngAfterViewInit() {
    this.drawer.closedStart.subscribe(() => {
      this.router.navigate([{outlets: {'drawer': null}}], {replaceUrl: true});
    });
  }
}
