import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatChipListHarness} from '@angular/material/chips/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {OsqueryFlowArgs} from '../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../testing';

import {OsqueryForm} from './osquery_form';



initTestEnvironment();

describe('OsqueryForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ReactiveFormsModule,
            FlowArgsFormModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function constructFixture(defaultFlowArgs: OsqueryFlowArgs = {}) {
    const fixture = TestBed.createComponent(OsqueryForm);
    fixture.detectChanges();
    fixture.componentInstance.resetFlowArgs(defaultFlowArgs);
    fixture.detectChanges();
    return fixture;
  }

  it('should display a code-editor,', () => {
    const fixture = constructFixture();

    const codeEditor = fixture.debugElement.query(By.css('app-code-editor'));
    expect(codeEditor).toBeTruthy();

    const browseSpecsButton =
        fixture.debugElement.query(By.css('.browse-tables-button'));
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display a browse tables button,', () => {
    const fixture = constructFixture();

    const browseSpecsButton =
        fixture.debugElement.query(By.css('.browse-tables-button'));
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display button for file collection settings and expand on click ',
     async () => {
       const fixture = constructFixture();
       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

       const expandButtonHarness = await harnessLoader.getHarness(
           MatButtonHarness.with({text: /Show file collection settings.*/}),
       );
       await expandButtonHarness.click();

       const fileCollectionContainer =
           fixture.debugElement.query(By.css('.collection-container'));
       expect(fileCollectionContainer).toBeTruthy();
     });

  it('should display button for low-level settings and expand on click ',
     async () => {
       const fixture = constructFixture();
       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

       const expandButtonHarness = await harnessLoader.getHarness(
           MatButtonHarness.with({text: /Show low-level settings.*/}),
       );
       await expandButtonHarness.click();

       const lowLevelSettingsContainer =
           fixture.debugElement.query(By.css('.settings-container'));
       expect(lowLevelSettingsContainer).toBeTruthy();
     });

  it('should have low-level and collection settings collapsed initially',
     () => {
       const fixture = constructFixture();

       const lowLevelSettingsContainer =
           fixture.debugElement.query(By.css('.settings-container'));
       const collectionContainer =
           fixture.debugElement.query(By.css('.collection-container'));

       expect(lowLevelSettingsContainer).toBeFalsy();

       expect(collectionContainer).toBeFalsy();
     });
  it('should have collection settings expanded when default flow args contain collection columns,',
     () => {
       const fixture = constructFixture({
         fileCollectionColumns: ['some column to collect files from'],
       });

       const collectionContainer =
           fixture.debugElement.query(By.css('.collection-container'));
       expect(collectionContainer).toBeTruthy();
     });

  it('updates the file collection form when a value is added', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    // Here we expand the file collection settings just like the user would
    // do. At the moment of writing this, it is not strictly needed, since
    // the harnesses would find the elements even if it is collapsed.
    const expandButtonHarness = await harnessLoader.getHarness(
        MatButtonHarness.with({text: /Show file collection settings.*/}),
    );
    await expandButtonHarness.click();

    const collectionListHarness =
        await harnessLoader.getHarness(MatChipListHarness);

    const inputHarness = await collectionListHarness.getInput();
    await inputHarness.setValue('column1');
    await inputHarness.blur();  // The value is submitted on blur

    const chips = await collectionListHarness.getChips();
    const valuesInForm =
        fixture.componentInstance.controls.fileCollectionColumns.value;

    expect(chips.length).toBe(1);
    expect(valuesInForm).toEqual(['column1']);
  });

  it('updates the file collection form when a value is removed', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    // Here we expand the file collection settings just like the user would
    // do. At the moment of writing this, it is not strictly needed, since
    // the harnesses would find the elements even if it is collapsed.
    const expandButtonHarness = await harnessLoader.getHarness(
        MatButtonHarness.with({text: /Show file collection settings.*/}),
    );
    await expandButtonHarness.click();

    const collectionListHarness =
        await harnessLoader.getHarness(MatChipListHarness);

    const inputHarness = await collectionListHarness.getInput();
    await inputHarness.setValue('column1');
    await inputHarness.blur();  // The value is submitted on blur

    const chips = await collectionListHarness.getChips();
    expect(chips.length).toBe(1);

    await chips[0].remove();
    const chipsAfterRemoval = await collectionListHarness.getChips();
    const valuesInFormAfterRemoval =
        fixture.componentInstance.form.controls.fileCollectionColumns.value;

    expect(chipsAfterRemoval.length).toBe(0);
    expect(valuesInFormAfterRemoval.length).toBe(0);
  });
});
