import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture} from '@angular/core/testing';
import {MatButtonToggleHarness} from '@angular/material/button-toggle/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

/** Sets the value for the input element matching the query in the fixture. */
export async function setInputValue(
    fixture: ComponentFixture<unknown>, query: string, value: string) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness =
      await harnessLoader.getHarness(MatInputHarness.with({selector: query}));
  await inputHarness.setValue(value);
}

/** Gets the value for the input element matching the query in the fixture. */
export async function getInputValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness =
      await harnessLoader.getHarness(MatInputHarness.with({selector: query}));
  return await inputHarness.getValue();
}

/**
 * Gets the value for the checkbox element matching the query in the fixture.
 */
export async function getCheckboxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const checkboxHarness = await harnessLoader.getHarness(
      MatCheckboxHarness.with({selector: query}));
  return await checkboxHarness.isChecked();
}

/** Selects the toggle button with text matching the query in the fixture. */
export async function selectButtonToggle(
    fixture: ComponentFixture<unknown>, query: string, text: string) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const toggle = await harnessLoader.getHarness(
      MatButtonToggleHarness.with({selector: query, text}));
  await toggle.check();
}

/**
 * Verifies whether the toggle button with text matching the query is selected
 * in the fixture.
 */
export async function isButtonToggleSelected(
    fixture: ComponentFixture<unknown>, query: string,
    text: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const toggle = await harnessLoader.getHarness(
      MatButtonToggleHarness.with({selector: query, text}));
  return await toggle.isChecked();
}

/**
 * Gets the selected option text in the selection box matching the query in the
 * fixture.
 */
export async function getSelectBoxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const selectionBoxHarness =
      await harnessLoader.getHarness(MatSelectHarness.with({selector: query}));
  return await selectionBoxHarness.getValueText();
}