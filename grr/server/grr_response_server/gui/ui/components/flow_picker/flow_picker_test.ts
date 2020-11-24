import {OverlayContainer} from '@angular/cdk/overlay';
import {DebugElement} from '@angular/core';
import {ComponentFixture, inject, TestBed, waitForAsync} from '@angular/core/testing';
import {MatAutocomplete, MatAutocompleteSelectedEvent} from '@angular/material/autocomplete';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowChips} from '@app/components/flow_picker/flow_chips';
import {FlowListItem, FlowListItemService} from '@app/components/flow_picker/flow_list_item';
import {assertNonNull} from '@app/lib/preconditions';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {ClientPageFacadeMock, mockClientPageFacade} from '@app/store/client_page_facade_test_util';
import {initTestEnvironment} from '@app/testing';
import {from} from 'rxjs';
import {FlowPicker} from './flow_picker';
import {FlowPickerModule} from './module';




initTestEnvironment();

function getAutocompleteInput(fixture: ComponentFixture<FlowPicker>):
    DebugElement {
  return fixture.debugElement.query(By.css('.autocomplete-field input'));
}


describe('FlowPicker Component', () => {
  let flowListItemService: Partial<FlowListItemService>;
  let clientPageFacade: ClientPageFacadeMock;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;

  beforeEach(waitForAsync(() => {
    clientPageFacade = mockClientPageFacade();

    flowListItemService = {
      flowsByCategory$: from([new Map([
        [
          'Collectors',
          [
            {
              name: 'ArtifactCollectorFlow',
              friendlyName: 'Forensic artifacts',
              description: 'Foo'
            },
            {
              name: 'OsqueryFlow',
              friendlyName: 'Osquery',
              description: 'Bar',
            },
          ]
        ],
        [
          'Browser',
          [
            {
              name: 'CollectBrowserHistory',
              friendlyName: 'Collect browser history',
              description: 'Something',
            },
          ]
        ],
      ])]),
      commonFlowNames$: from([['Osquery']]),
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowPickerModule,
          ],

          providers: [
            {
              provide: FlowListItemService,
              useFactory: () => flowListItemService
            },
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
          ]
        })
        .compileComponents();

    inject([OverlayContainer], (oc: OverlayContainer) => {
      overlayContainer = oc;
      overlayContainerElement = oc.getContainerElement();
    })();
  }));

  afterEach(() => {
    overlayContainer.ngOnDestroy();
  });

  it('shows nothing by default', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const matOptions = overlayContainerElement.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(0);
    const matOptGroups =
        overlayContainerElement.querySelectorAll('mat-optgroup');
    expect(matOptGroups.length).toBe(0);
  });

  it('shows an overview panel on click', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    expect(overlayContainerElement.querySelectorAll('flows-overview').length)
        .toBe(0);

    const input = getAutocompleteInput(fixture);
    input.nativeElement.click();
    fixture.detectChanges();

    expect(overlayContainerElement.querySelectorAll('flows-overview').length)
        .toBe(1);
  });

  it('hides an overview panel on input', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.click();
    fixture.detectChanges();

    expect(overlayContainerElement.querySelectorAll('flows-overview').length)
        .toBe(1);

    fixture.componentInstance.textInput.setValue('arti');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(overlayContainerElement.querySelectorAll('flows-overview').length)
        .toBe(0);
  });

  it('selects a Flow when a a link in overview panel is clicked', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.click();
    fixture.detectChanges();

    const links = overlayContainerElement.querySelectorAll('flows-overview a');
    const link = Array.from(links).find(
        l => l.textContent?.includes('Forensic artifacts'));
    assertNonNull(link);
    link.dispatchEvent(new MouseEvent('click'));
    fixture.detectChanges();

    expect(overlayContainerElement.querySelectorAll('flows-overview').length)
        .toBe(0);

    expect(fixture.componentInstance.textInput.value)
        .toBe('Forensic artifacts');
    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('ArtifactCollectorFlow');
  });

  it('filters Flows that match text input', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.componentInstance.textInput.setValue('arti');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const matOptions = overlayContainerElement.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(1);
    expect(matOptions[0].textContent).toContain('Forensic artifacts');

    const matOptGroups =
        overlayContainerElement.querySelectorAll('mat-optgroup');
    expect(matOptGroups.length).toBe(1);
    expect(matOptGroups[0].textContent).toContain('Collectors');
  });

  it('highlights the matching Flow part', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.componentInstance.textInput.setValue('arti');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const nameElements =
        overlayContainerElement.querySelectorAll('mat-option .flow-title span');
    expect(nameElements.length).toBe(3);

    expect(nameElements[0].textContent).toBe('Forensic ');
    expect(nameElements[0].classList.contains('highlight')).toBeFalse();

    expect(nameElements[1].textContent).toBe('arti');
    expect(nameElements[1].classList.contains('highlight')).toBeTrue();

    expect(nameElements[2].textContent).toBe('facts');
    expect(nameElements[2].classList.contains('highlight')).toBeFalse();
  });

  it('filters Categories that match the input', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.componentInstance.textInput.setValue('collector');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const matOptions = overlayContainerElement.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('Forensic artifacts');
    expect(matOptions[1].textContent).toContain('Osquery');

    const matOptGroups =
        overlayContainerElement.querySelectorAll('mat-optgroup');
    expect(matOptGroups.length).toBe(1);
    expect(matOptGroups[0].textContent).toContain('Collectors');
  });

  it('highlights the matching Category part', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.componentInstance.textInput.setValue('collector');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const nameElements = overlayContainerElement.querySelectorAll(
        'mat-optgroup span.category-title');
    expect(nameElements.length).toBe(2);

    expect(nameElements[0].textContent).toBe('Collector');
    expect(nameElements[0].classList.contains('highlight')).toBeTrue();

    expect(nameElements[1].textContent).toBe('s');
    expect(nameElements[1].classList.contains('highlight')).toBeFalse();
  });

  it('selects a Flow on autocomplete change', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.componentInstance.textInput.setValue('brows');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const flowListItem: FlowListItem = {
      name: 'CollectBrowserHistory',
      friendlyName: 'Collect browser history',
      description: '',
    };
    const matAutocomplete: MatAutocomplete =
        fixture.debugElement.query(By.directive(MatAutocomplete))
            .componentInstance;
    matAutocomplete.optionSelected.emit({
      option: {value: flowListItem},
    } as MatAutocompleteSelectedEvent);
    fixture.detectChanges();

    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('CollectBrowserHistory');
  });

  it('deselects the Flow on X button click', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const input = getAutocompleteInput(fixture);
    input.nativeElement.click();
    fixture.componentInstance.textInput.setValue('browser');
    input.nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const flowListItem: FlowListItem = {
      name: 'CollectBrowserHistory',
      friendlyName: 'Collect browser history',
      description: '',
    };
    const matAutocomplete: MatAutocomplete =
        fixture.debugElement.query(By.directive(MatAutocomplete))
            .componentInstance;
    matAutocomplete.optionSelected.emit({
      option: {value: flowListItem},
    } as MatAutocompleteSelectedEvent);
    fixture.detectChanges();

    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('CollectBrowserHistory');

    const clearButton =
        fixture.debugElement.query(By.css('.readonly-field button'));
    assertNonNull(clearButton);
    clearButton.nativeElement.click();
    fixture.detectChanges();

    expect(clientPageFacade.stopFlowConfiguration).toHaveBeenCalled();
  });

  it('selects a Flow when FlowChips emits flowSelected event', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    const flowChips: FlowChips =
        fixture.debugElement.query(By.directive(FlowChips)).componentInstance;
    flowChips.flowSelected.emit({
      name: 'ArtifactCollectorFlow',
      friendlyName: 'Forensic artifacts',
      description: 'Foo'
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.textInput.value)
        .toBe('Forensic artifacts');
    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('ArtifactCollectorFlow');
  });

  it('hides FlowChips when a Flow is selected', async () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();
    await fixture.whenRenderingDone();

    let flowChips = fixture.debugElement.query(By.directive(FlowChips));
    expect(flowChips).not.toBeNull();

    clientPageFacade.selectedFlowDescriptorSubject.next({
      category: 'Browser',
      name: 'CollectBrowserHistory',
      friendlyName: 'Collect browser history',
      defaultArgs: {},
    });
    fixture.detectChanges();

    flowChips = fixture.debugElement.query(By.directive(FlowChips));
    expect(flowChips).toBeNull();
  });
});
