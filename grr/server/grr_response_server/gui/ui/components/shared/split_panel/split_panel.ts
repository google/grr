import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  Input,
  OnInit,
  Renderer2,
  signal,
} from '@angular/core';

/**
 * A component that provides two resizable panels, split either horizontally or vertically,
 * with a draggable gutter in between. Implemented manually without third-party libraries.
 *
 * Usage:
 * <my-manual-split-panel direction="horizontal" [initialSize]="30">
 *   <div slot="panel1">Panel 1 Content</div>
 *   <div slot="panel2">Panel 2 Content</div>
 * </my-manual-split-panel>
 *
 * Make sure the host element of my-manual-split-panel has defined dimensions (e.g., height: 100%).
 */
@Component({
  selector: 'split-panel',
  templateUrl: './split_panel.ng.html',
  styleUrls: ['./split_panel.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SplitPanel implements OnInit {
  private readonly renderer = inject(Renderer2);
  private readonly elementRef = inject(ElementRef<HTMLElement>);

  /** Direction of the split: 'horizontal' (side-by-side) or 'vertical' (top-and-bottom). */
  @Input() direction: 'horizontal' | 'vertical' = 'horizontal';

  /** Initial size of the first panel in percentage. */
  @Input() initialSize = 50;

  protected readonly gutterSize = 8;

  protected firstPanelSize = signal<number>(50);
  protected isDragging = false;

  private dragStartPos = 0;
  private dragStartSizePx = 0;

  private unlistenMousemove?: () => void;
  private unlistenMouseup?: () => void;

  ngOnInit() {
    this.firstPanelSize.set(this.initialSize);
  }

  startDrag(event: MouseEvent) {
    event.preventDefault(); // Prevent text selection
    this.isDragging = true;

    const firstPanel =
      this.elementRef.nativeElement.querySelector('.panel:first-child');
    if (!firstPanel) return;

    const firstPanelRect = firstPanel.getBoundingClientRect();

    if (this.direction === 'horizontal') {
      this.dragStartPos = event.clientX;
      this.dragStartSizePx = firstPanelRect.width;
    } else {
      this.dragStartPos = event.clientY;
      this.dragStartSizePx = firstPanelRect.height;
    }

    this.unlistenMousemove = this.renderer.listen(
      'document',
      'mousemove',
      this.onDrag.bind(this),
    );
    this.unlistenMouseup = this.renderer.listen(
      'document',
      'mouseup',
      this.stopDrag.bind(this),
    );

    // Add class to body to prevent text selection globally
    this.renderer.addClass(document.body, 'split-panel-dragging');
  }

  onDrag(event: MouseEvent) {
    if (!this.isDragging) return;
    event.preventDefault();

    const containerRect = this.elementRef.nativeElement.getBoundingClientRect();
    let newSizePercent: number;

    if (this.direction === 'horizontal') {
      const deltaX = event.clientX - this.dragStartPos;
      const containerWidth = containerRect.width;
      if (containerWidth === 0) return;
      const newWidth = this.dragStartSizePx + deltaX;
      newSizePercent = (newWidth / containerWidth) * 100;
    } else {
      // vertical
      const deltaY = event.clientY - this.dragStartPos;
      const containerHeight = containerRect.height;
      if (containerHeight === 0) return;
      const newHeight = this.dragStartSizePx + deltaY;
      newSizePercent = (newHeight / containerHeight) * 100;
    }

    this.firstPanelSize.set(Math.max(0, Math.min(100, newSizePercent)));
  }

  stopDrag(event: MouseEvent) {
    if (this.isDragging) {
      this.isDragging = false;

      if (this.unlistenMousemove) this.unlistenMousemove();
      if (this.unlistenMouseup) this.unlistenMouseup();
      this.unlistenMousemove = undefined;
      this.unlistenMouseup = undefined;

      this.renderer.removeClass(document.body, 'split-panel-dragging');
    }
  }
}
