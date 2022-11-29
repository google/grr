import {Directive, Host, Input, OnChanges, SimpleChanges} from '@angular/core';
import {ActivatedRoute, RouterLinkWithHref} from '@angular/router';

/** Applies [routerLink] to elements having [drawerLink]. */
@Directive({selector: 'a[drawerLink],area[drawerLink],button[drawerLink]'})
export class DrawerRouterLinkWithHref extends RouterLinkWithHref {
}

/** Creates a [routerLink] opening the given route in the Drawer. */
@Directive({selector: 'a[drawerLink],area[drawerLink],button[drawerLink]'})
export class DrawerLink implements OnChanges {
  @Input() drawerLink?: Array<string|{}>;

  constructor(
      @Host() private readonly routerLink: DrawerRouterLinkWithHref,
      private readonly activatedRoute: ActivatedRoute) {}

  ngOnChanges(changes: SimpleChanges) {
    if (this.drawerLink?.length) {
      // Outlet name 'drawer' needs to be a literal string to avoid
      // uglification.
      this.routerLink.routerLink = [{outlets: {'drawer': this.drawerLink}}];
    } else {
      this.routerLink.routerLink = [];
    }

    this.routerLink.relativeTo = this.activatedRoute.root;
    this.routerLink.ngOnChanges(changes);
  }
}
