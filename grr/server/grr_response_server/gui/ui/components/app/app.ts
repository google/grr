import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ActivatedRouteSnapshot, ActivationEnd, Router} from '@angular/router';
import {filter, map} from 'rxjs/operators';

import {makeLegacyLink, makeLegacyLinkFromRoute} from '../../lib/routing';

/** Recursively searches a route and all child routes to fulfill a predicate. */
function findRouteWith(
    route: ActivatedRouteSnapshot,
    pred: ((route: ActivatedRouteSnapshot) => boolean)): ActivatedRouteSnapshot|
    undefined {
  if (pred(route)) {
    return route;
  }
  for (const child of route.children) {
    const result = findRouteWith(child, pred);
    if (result !== undefined) {
      return result;
    }
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

  constructor(private readonly router: Router) {}
}
