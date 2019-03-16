/**
 * @license
 * Copyright 2006 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

// This file contains typedefs and externs that are needed by the Closure Compiler.

/**
 * @typedef {{
 *   px: number,
 *   py: number,
 *   isZooming: boolean,
 *   isPanning: boolean,
 *   is2DPan: boolean,
 *   cancelNextDblclick: boolean,
 *   initializeMouseDown:
 *       function(!Event, !Dygraph, !DygraphInteractionContext)
 * }}
 */
var DygraphInteractionContext;

/**
 * Point structure.
 *
 * xval_* and yval_* are the original unscaled data values,
 * while x_* and y_* are scaled to the range (0.0-1.0) for plotting.
 * yval_stacked is the cumulative Y value used for stacking graphs,
 * and bottom/top/minus/plus are used for error bar graphs.
 *
 * @typedef {{
 *     idx: number,
 *     name: string,
 *     x: ?number,
 *     xval: ?number,
 *     y_bottom: ?number,
 *     y: ?number,
 *     y_stacked: ?number,
 *     y_top: ?number,
 *     yval_minus: ?number,
 *     yval: ?number,
 *     yval_plus: ?number,
 *     yval_stacked
 * }}
 */
Dygraph.PointType;
