/**
 * @license
 * Copyright 2006 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

// TODO(danvk): move the Dygraph definitions out of here once I closure-ify dygraphs.js
/**
 * @param {!HTMLDivElement|string} div
 * @param {DygraphDataArray|
 *     GVizDataTable|
 *     string|
 *     function():(DygraphDataArray|GVizDataTable|string)} file
 * @param {Object} attrs
 * @constructor
 */
function Dygraph(div, file, attrs) {}

/** @type {string} */
Dygraph.NAME;

/** @type {string} */
Dygraph.VERSION;

/** @type {function(): string} */
Dygraph.toString;

/** @type {function(Event, Dygraph, DygraphInteractionContext)} */
Dygraph.startPan;

/** @type {function(Event, Dygraph, DygraphInteractionContext)} */
Dygraph.movePan;

/** @type {function(Event, Dygraph, DygraphInteractionContext)} */
Dygraph.endPan;

/** @type {function(?string): boolean} */
Dygraph.prototype.isZoomed;

/** @type {function(): string} */
Dygraph.prototype.toString;

/** @type {function(string, string)} */
Dygraph.prototype.getOption;

/** @type {function(): number} */
Dygraph.prototype.rollPeriod;

/** @type {function(): ?Array.<number>} */
Dygraph.prototype.xAxisRange;

/** @type {function(): Array.<number>} */
Dygraph.prototype.xAxisExtremes;

/** @type {function(number): ?Array.<number>} */
Dygraph.prototype.yAxisRange;

/** @type {function(): Array.<Array.<number>>} */
Dygraph.prototype.yAxisRanges;

/** @type {function(?number, ?number, ?number): Array.<?number>} */
Dygraph.prototype.toDomCoords

/** @type {function(?number): ?number} */
Dygraph.prototype.toDomXCoord;

/** @type {function(?number, ?number): ?number} */
Dygraph.prototype.toDomYCoord;

/** @type {function(?number, ?number, ?number): Array.<?number>} */
Dygraph.prototype.toDataCoords;

/** @type {function(?number): ?number} */
Dygraph.prototype.toDataXCoord;

/** @type {function(?number, ?number): ?number} */
Dygraph.prototype.toDataYCoord;

/** @type {function(?number, ?number): ?number} */
Dygraph.prototype.toPercentYCoord;

/** @type {function(?number): ?number} */
Dygraph.prototype.toPercentXCoord;

/** @type {function(): number} */
Dygraph.prototype.numColumns;

/** @type {function(): number} */
Dygraph.prototype.numRows;

/** @type {function(number, number)} */
Dygraph.prototype.getValue;

/** @type {function()} */
Dygraph.prototype.destroy;

/** @type {function()} */
Dygraph.prototype.getColors;

/** @type {function(string)} */
Dygraph.prototype.getPropertiesForSeries;

/** @type {function()} */
Dygraph.prototype.resetZoom;

/** @type {function(): {x, y, w, h}} */
Dygraph.prototype.getArea;

/** @type {function(Object): Array.<number>} */
Dygraph.prototype.eventToDomCoords;

/** @type {function(number, string, boolean): boolean} */
Dygraph.prototype.setSelection;

/** @type {function()} */
Dygraph.prototype.clearSelection;

/** @type {function(): number} */
Dygraph.prototype.getSelection;

/** @type {function(): string} */
Dygraph.prototype.getHighlightSeries;

/** @type {function(): boolean} */
Dygraph.prototype.isSeriesLocked;

/** @type {function(): number} */
Dygraph.prototype.numAxes;

/** @type {function(Object, Boolean=)} */
Dygraph.prototype.updateOptions;

/** @type {function(number, number)} */
Dygraph.prototype.resize;

/** @type {function(number)} */
Dygraph.prototype.adjustRoll;

/** @type {function(): Array.<boolean>} */
Dygraph.prototype.visibility;

/** @type {function(number, boolean)} */
Dygraph.prototype.setVisibility;

/** @type {function(Array.<Object>, boolean)} */
Dygraph.prototype.setAnnotations;

/** @type {function(): Array.<Object>} */
Dygraph.prototype.annotations;

/** @type {function(): ?Array.<string>} */
Dygraph.prototype.getLabels;

/** @type {function(string): ?number} */
Dygraph.prototype.indexFromSetName;

/** @type {function(function(!Dygraph))} */
Dygraph.prototype.ready;
