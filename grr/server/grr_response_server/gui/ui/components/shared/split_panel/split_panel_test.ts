import {TestElement} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, Input, ViewChild} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';
import {SplitPanel} from './split_panel';
import {SplitPanelHarness} from './testing/split_panel_harness';

initTestEnvironment();

function getNativeElement(element: TestElement): Element {
  // tslint:disable-next-line:no-any
  return (element as any).element;
}

function performDrag(
  gutterHarnessEl: TestElement,
  deltaX: number,
  deltaY: number,
) {
  const gutterEl = getNativeElement(gutterHarnessEl);
  const rect = gutterEl.getBoundingClientRect();
  const startX = rect.left + rect.width / 2;
  const startY = rect.top + rect.height / 2;
  const endX = startX + deltaX;
  const endY = startY + deltaY;

  const mouseDownEvent = new MouseEvent('mousedown', {
    clientX: startX,
    clientY: startY,
    button: 0,
    buttons: 1,
    bubbles: true,
  });
  gutterEl.dispatchEvent(mouseDownEvent);

  const mouseMoveEvent = new MouseEvent('mousemove', {
    clientX: endX,
    clientY: endY,
    buttons: 1,
    bubbles: true,
  });
  document.dispatchEvent(mouseMoveEvent);

  const mouseUpEvent = new MouseEvent('mouseup', {
    clientX: endX,
    clientY: endY,
    button: 0,
    bubbles: true,
  });
  document.dispatchEvent(mouseUpEvent);
}

@Component({
  imports: [SplitPanel],
  template: `
    <div style="height: 500px; width: 800px;">
      <split-panel
        [direction]="direction"
        [initialSize]="initialSize">
        <div slot="panel1">Panel 1</div>
        <div slot="panel2">Panel 2</div>
      </split-panel>
    </div>
  `,
})
class TestHostComponent {
  @Input() direction: 'horizontal' | 'vertical' = 'horizontal';
  @Input() initialSize = 50;

  @ViewChild(SplitPanel) splitPanel!: SplitPanel;
}

async function createComponent(
  direction: 'horizontal' | 'vertical',
  initialSize: number,
) {
  const fixture = TestBed.createComponent(TestHostComponent);
  fixture.componentRef.setInput('direction', direction);
  fixture.componentRef.setInput('initialSize', initialSize);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    SplitPanelHarness,
  );

  return {fixture, harness};
}

describe('Split Panel Component', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent, NoopAnimationsModule],
    }).compileComponents();
  });

  it('is created', async () => {
    const {fixture, harness} = await createComponent('horizontal', 50);

    expect(fixture.componentInstance).toBeTruthy();
    expect(harness).toBeDefined();
  });

  it('can create horizontal split with correct sizes and direction', async () => {
    const {harness} = await createComponent('horizontal', 30);

    expect(await harness.getDirection()).toBe('horizontal');
    expect(await harness.getPanel1SizePercent()).toBe(30);
  });

  it('should resize horizontal panels when dragging the gutter', async () => {
    const {harness, fixture} = await createComponent('horizontal', 30);

    const gutter = await harness.gutter();
    // Drag to the right by 80px (10% of 800px width)
    performDrag(gutter, 80, 0);
    fixture.detectChanges();

    const newSize = await harness.getPanel1SizePercent();
    // Initial 30% + 10% = 40%
    expect(newSize).toBeCloseTo(40, 1);
  });

  it('should initialize vertical split with correct sizes and direction', async () => {
    const {harness} = await createComponent('vertical', 60);

    expect(await harness.getDirection()).toBe('vertical');
    expect(await harness.getPanel1SizePercent()).toBe(60);
  });

  it('should resize vertical panels when dragging the gutter', async () => {
    const {harness, fixture} = await createComponent('vertical', 60);

    const gutter = await harness.gutter();
    // Drag down by 50px (10% of 500px height)
    performDrag(gutter, 0, 50);
    fixture.detectChanges();

    const newSize = await harness.getPanel1SizePercent();
    // Initial 60% + 10% = 70%
    expect(newSize).toBeCloseTo(70, 1);
  });

  it('should apply and remove body classes during drag', async () => {
    const {harness, fixture} = await createComponent('horizontal', 30);

    const gutterHarnessEl = await harness.gutter();
    const gutterEl = getNativeElement(gutterHarnessEl);
    const rect = gutterEl.getBoundingClientRect();
    const x = rect.left + 2;
    const y = rect.top + 2;

    gutterEl.dispatchEvent(
      new MouseEvent('mousedown', {
        clientX: x,
        clientY: y,
        button: 0,
        buttons: 1,
        bubbles: true,
      }),
    );
    fixture.detectChanges();
    expect(document.body.classList).toContain('split-panel-dragging');

    document.dispatchEvent(
      new MouseEvent('mousemove', {
        clientX: x + 50,
        clientY: y,
        buttons: 1,
        bubbles: true,
      }),
    );
    fixture.detectChanges();
    expect(document.body.classList).toContain('split-panel-dragging');

    document.dispatchEvent(
      new MouseEvent('mouseup', {
        clientX: x + 50,
        clientY: y,
        button: 0,
        bubbles: true,
      }),
    );
    fixture.detectChanges();
    expect(document.body.classList).not.toContain('split-panel-dragging');
  });
});
