import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, BaseRouteReuseStrategy, Data, Route} from '@angular/router';

/** Prefix of the legacy UI route. */
export const LEGACY_ROUTE_PREFIX = '/legacy';

/**
 * Data for tracking page view with Google Analytics.
 *
 *  We don't want to track any sensible information (e.g. client identification)
 *  when tracking page views. Thus, we add information on how to redact it
 *  together with the route.
 */
export declare interface AnalyticsPageView {
  pageTitle?: string;
  pagePath?: string;
  pageLocation?: string;
  pageReferrer?: string;
}

/** Extra data to be passed around in Grr routes. */
export declare interface GrrRouteData extends Data {
  legacyLink?: string;
  reuseComponent?: boolean;
  collapseClientHeader?: boolean;
  pageViewTracking?: AnalyticsPageView;
}

/** Same as Route, but with typed `data`. */
export declare interface GrrRoute extends Route {
  data?: GrrRouteData;
}


/** Same as ActivatedRouteSnapshot, but with typed `data`. */
export declare interface GrrActivatedRouteSnapshot extends
    ActivatedRouteSnapshot {
  data: GrrRouteData;
}

/**
 * Strategy to reuse Components if two Routes declare the same component and
 * specify reuseComponent.
 */
@Injectable({providedIn: 'root'})
export class SameComponentRouteReuseStrategy extends BaseRouteReuseStrategy {
  override shouldReuseRoute(
      future: GrrActivatedRouteSnapshot,
      curr: GrrActivatedRouteSnapshot): boolean {
    const reuseCurr = curr.data.reuseComponent ?? false;
    const reuseFuture = future.data.reuseComponent ?? false;
    const sameComponent = future.component === curr.component;
    return (reuseCurr && reuseFuture && sameComponent) ||
        super.shouldReuseRoute(future, curr);
  }
}

/** Constructs a link to the old UI by parsing a Route's data.legacyLink. */
export function makeLegacyLinkFromRoute(route: GrrActivatedRouteSnapshot):
    string {
  let legacyLink: string = route.data.legacyLink ?? '';
  let currentSnapshot: ActivatedRouteSnapshot|null = route;

  // First, replace placeholders like :clientId from the route's path
  // parameters. Start at the current route and then traverse to all parent
  // routes to have the parameters of child routes override parameters of parent
  // routes.
  while (currentSnapshot) {
    for (const [key, value] of Object.entries(currentSnapshot.params)) {
      legacyLink = legacyLink.replace(`:${key}`, value);
    }
    currentSnapshot = currentSnapshot.parent;
  }

  for (const [key, value] of Object.entries(route.queryParams)) {
    legacyLink = legacyLink.replace(`:${key}`, encodeURIComponent(value));
  }

  return makeLegacyLink(legacyLink);
}

/** Returns a link to the old UI, e.g. provide '#/clients/'. */
export function makeLegacyLink(suffix: string = ''): string {
  const url = new URL(window.location.origin);
  url.pathname = LEGACY_ROUTE_PREFIX;
  url.hash = '';
  return url.toString() + suffix;
}
