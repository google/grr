import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, input, Type} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from './collapsible_container';
import {CollapsibleContainerHarness} from './testing/collapsible_container_harness';

initTestEnvironment();

@Component({
  template: `
      <collapsible-container [state]="state()">
        <collapsible-title>Test title</collapsible-title>
        <collapsible-content>Test content</collapsible-content>
      </collapsible-container>`,
  imports: [CollapsibleContainer, CollapsibleTitle, CollapsibleContent],
})
class TestCollapsibleContainerWithInitialState {
  readonly state = input.required<CollapsibleState>();
}

@Component({
  template: `
      <collapsible-container>
        <collapsible-title>Test title</collapsible-title>
        <collapsible-content>Test content</collapsible-content>
      </collapsible-container>`,
  imports: [CollapsibleContainer, CollapsibleTitle, CollapsibleContent],
})
class TestCollapsibleContainerWithDefaultState {}

async function createComponent<
  T extends
    | TestCollapsibleContainerWithInitialState
    | TestCollapsibleContainerWithDefaultState,
>(testComponent: Type<T>, initialState?: CollapsibleState) {
  const fixture = TestBed.createComponent(testComponent);
  if (initialState !== undefined) {
    fixture.componentRef.setInput('state', initialState);
  }

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollapsibleContainerHarness,
  );
  return {fixture, harness};
}

describe('Collapsible Content component', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        TestCollapsibleContainerWithInitialState,
        TestCollapsibleContainerWithDefaultState,
        NoopAnimationsModule,
      ],
    }).compileComponents();
  });

  it('is created', async () => {
    const {fixture} = await createComponent(
      TestCollapsibleContainerWithDefaultState,
    );

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows correct header text', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithDefaultState,
    );

    expect(await harness.getHeaderText()).toContain('Test title');
  });

  it('initially expands content if not specified', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithDefaultState,
    );

    expect(await harness.showsCollapseIcon()).toBeTrue();
    expect(await harness.isContentVisible()).toBeTrue();
    expect(await harness.getContentText()).toBe('Test content');
  });

  it('initially collapses content if specified', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithInitialState,
      CollapsibleState.COLLAPSED,
    );

    expect(await harness.showsExpandIcon()).toBeTrue();
    expect(await harness.isContentVisible()).toBeFalse();
  });

  it('initially expands content if specified', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithInitialState,
      CollapsibleState.EXPANDED,
    );

    expect(await harness.showsCollapseIcon()).toBeTrue();
    expect(await harness.isContentVisible()).toBeTrue();
  });

  it('collapses content on button click', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithInitialState,
      CollapsibleState.EXPANDED,
    );

    const collapseButton = await harness.toggleButton();
    await collapseButton.click();

    expect(await harness.showsExpandIcon()).toBeTrue();
    expect(await harness.isContentVisible()).toBeFalse();
  });

  it('expands content again on double button click', async () => {
    const {harness} = await createComponent(
      TestCollapsibleContainerWithInitialState,
      CollapsibleState.EXPANDED,
    );

    const toggleButton = await harness.toggleButton();
    await toggleButton.click();
    await toggleButton.click();

    expect(await harness.showsCollapseIcon()).toBeTrue();
    expect(await harness.isContentVisible()).toBeTrue();
  });
});
