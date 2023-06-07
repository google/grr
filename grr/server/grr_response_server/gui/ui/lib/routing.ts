import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, BaseRouteReuseStrategy, Route} from '@angular/router';

/** Prefix of the legacy UI route. */
export const LEGACY_ROUTE_PREFIX = '/legacy';

declare interface LegacyLink {
  legacyLink: string;
}

declare interface ReuseComponent {
  reuseComponent?: boolean;
}

declare interface RouteWithGenericData<T extends Route['data']> extends Route {
  data?: T;
}

/** A Route with a template string ('#/clients/:id') to link to the old UI. */
export type RouteWithLegacyLink = RouteWithGenericData<LegacyLink>;
/**
 * A Route that can specify to reuse its component if the next Route would use
 * the same.
 */
export type RouteWithReuseComponent = RouteWithGenericData<ReuseComponent>;

/** Routes with `data.legacyLink` that link to the old UI. */
export type RoutesWithLegacyLinks = RouteWithLegacyLink[];

/** Routes with `data.legacyLink` that link to the old UI. */
export type RoutesWithReuseComponent = RouteWithReuseComponent[];

/** Routes with custom data to specify legacy links & reusing components. */
export type RouteWithCustomData =
    RouteWithGenericData<LegacyLink&ReuseComponent>;

/** Routes with custom data to specify legacy links & reusing components. */
export type RoutesWithCustomData = RouteWithCustomData[];

/**
 * Strategy to reuse Components if two Routes declare the same component and
 * specify reuseComponent.
 */
@Injectable({providedIn: 'root'})
export class SameComponentRouteReuseStrategy extends BaseRouteReuseStrategy {
  override shouldReuseRoute(
      future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    const reuseCurr = curr.data['reuseComponent'] ?? false;
    const reuseFuture = future.data['reuseComponent'] ?? false;
    const sameComponent = future.component === curr.component;
    return (reuseCurr && reuseFuture && sameComponent) ||
        super.shouldReuseRoute(future, curr);
  }
}

/** Constructs a link to the old UI by parsing a Route's data.legacyLink. */
export function makeLegacyLinkFromRoute(route: ActivatedRouteSnapshot): string {
  let legacyLink: string = route.data['legacyLink'] ?? '';
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
