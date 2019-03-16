/**
 * @license
 * Copyright 2006 Dan Vanderkam (danvdk@gmail.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

/**
 * @fileoverview Creates an interactive, zoomable graph based on a CSV file or
 * string. Dygraph can handle multiple series with or without error bars. The
 * date/value ranges will be automatically set. Dygraph uses the
 * &lt;canvas&gt; tag, so it only works in FF1.5+.
 * @author danvdk@gmail.com (Dan Vanderkam)

  Usage:
   <div id="graphdiv" style="width:800px; height:500px;"></div>
   <script type="text/javascript">
     new Dygraph(document.getElementById("graphdiv"),
                 "datafile.csv",  // CSV file with headers
                 { }); // options
   </script>

 The CSV file is of the form

   Date,SeriesA,SeriesB,SeriesC
   YYYYMMDD,A1,B1,C1
   YYYYMMDD,A2,B2,C2

 If the 'errorBars' option is set in the constructor, the input should be of
 the form
   Date,SeriesA,SeriesB,...
   YYYYMMDD,A1,sigmaA1,B1,sigmaB1,...
   YYYYMMDD,A2,sigmaA2,B2,sigmaB2,...

 If the 'fractions' option is set, the input should be of the form:

   Date,SeriesA,SeriesB,...
   YYYYMMDD,A1/B1,A2/B2,...
   YYYYMMDD,A1/B1,A2/B2,...

 And error bars will be calculated automatically using a binomial distribution.

 For further documentation and examples, see http://dygraphs.com/

 */

// For "production" code, this gets set to false by uglifyjs.
if (typeof(DEBUG) === 'undefined') DEBUG=true;

var Dygraph = (function() {
/*global DygraphLayout:false, DygraphCanvasRenderer:false, DygraphOptions:false, G_vmlCanvasManager:false,ActiveXObject:false */
"use strict";

/**
 * Creates an interactive, zoomable chart.
 *
 * @constructor
 * @param {div | String} div A div or the id of a div into which to construct
 * the chart.
 * @param {String | Function} file A file containing CSV data or a function
 * that returns this data. The most basic expected format for each line is
 * "YYYY/MM/DD,val1,val2,...". For more information, see
 * http://dygraphs.com/data.html.
 * @param {Object} attrs Various other attributes, e.g. errorBars determines
 * whether the input data contains error ranges. For a complete list of
 * options, see http://dygraphs.com/options.html.
 */
var Dygraph = function(div, data, opts, opt_fourth_param) {
  // These have to go above the "Hack for IE" in __init__ since .ready() can be
  // called as soon as the constructor returns. Once support for OldIE is
  // dropped, this can go down with the rest of the initializers.
  this.is_initial_draw_ = true;
  this.readyFns_ = [];

  if (opt_fourth_param !== undefined) {
    // Old versions of dygraphs took in the series labels as a constructor
    // parameter. This doesn't make sense anymore, but it's easy to continue
    // to support this usage.
    console.warn("Using deprecated four-argument dygraph constructor");
    this.__old_init__(div, data, opts, opt_fourth_param);
  } else {
    this.__init__(div, data, opts);
  }
};

Dygraph.NAME = "Dygraph";
Dygraph.VERSION = "1.1.1";
Dygraph.__repr__ = function() {
  return "[" + Dygraph.NAME + " " + Dygraph.VERSION + "]";
};

/**
 * Returns information about the Dygraph class.
 */
Dygraph.toString = function() {
  return Dygraph.__repr__();
};

// Various default values
Dygraph.DEFAULT_ROLL_PERIOD = 1;
Dygraph.DEFAULT_WIDTH = 480;
Dygraph.DEFAULT_HEIGHT = 320;

// For max 60 Hz. animation:
Dygraph.ANIMATION_STEPS = 12;
Dygraph.ANIMATION_DURATION = 200;

// Label constants for the labelsKMB and labelsKMG2 options.
// (i.e. '100000' -> '100K')
Dygraph.KMB_LABELS = [ 'K', 'M', 'B', 'T', 'Q' ];
Dygraph.KMG2_BIG_LABELS = [ 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y' ];
Dygraph.KMG2_SMALL_LABELS = [ 'm', 'u', 'n', 'p', 'f', 'a', 'z', 'y' ];

// These are defined before DEFAULT_ATTRS so that it can refer to them.
/**
 * @private
 * Return a string version of a number. This respects the digitsAfterDecimal
 * and maxNumberWidth options.
 * @param {number} x The number to be formatted
 * @param {Dygraph} opts An options view
 */
Dygraph.numberValueFormatter = function(x, opts) {
  var sigFigs = opts('sigFigs');

  if (sigFigs !== null) {
    // User has opted for a fixed number of significant figures.
    return Dygraph.floatFormat(x, sigFigs);
  }

  var digits = opts('digitsAfterDecimal');
  var maxNumberWidth = opts('maxNumberWidth');

  var kmb = opts('labelsKMB');
  var kmg2 = opts('labelsKMG2');

  var label;

  // switch to scientific notation if we underflow or overflow fixed display.
  if (x !== 0.0 &&
      (Math.abs(x) >= Math.pow(10, maxNumberWidth) ||
       Math.abs(x) < Math.pow(10, -digits))) {
    label = x.toExponential(digits);
  } else {
    label = '' + Dygraph.round_(x, digits);
  }

  if (kmb || kmg2) {
    var k;
    var k_labels = [];
    var m_labels = [];
    if (kmb) {
      k = 1000;
      k_labels = Dygraph.KMB_LABELS;
    }
    if (kmg2) {
      if (kmb) console.warn("Setting both labelsKMB and labelsKMG2. Pick one!");
      k = 1024;
      k_labels = Dygraph.KMG2_BIG_LABELS;
      m_labels = Dygraph.KMG2_SMALL_LABELS;
    }

    var absx = Math.abs(x);
    var n = Dygraph.pow(k, k_labels.length);
    for (var j = k_labels.length - 1; j >= 0; j--, n /= k) {
      if (absx >= n) {
        label = Dygraph.round_(x / n, digits) + k_labels[j];
        break;
      }
    }
    if (kmg2) {
      // TODO(danvk): clean up this logic. Why so different than kmb?
      var x_parts = String(x.toExponential()).split('e-');
      if (x_parts.length === 2 && x_parts[1] >= 3 && x_parts[1] <= 24) {
        if (x_parts[1] % 3 > 0) {
          label = Dygraph.round_(x_parts[0] /
              Dygraph.pow(10, (x_parts[1] % 3)),
              digits);
        } else {
          label = Number(x_parts[0]).toFixed(2);
        }
        label += m_labels[Math.floor(x_parts[1] / 3) - 1];
      }
    }
  }

  return label;
};

/**
 * variant for use as an axisLabelFormatter.
 * @private
 */
Dygraph.numberAxisLabelFormatter = function(x, granularity, opts) {
  return Dygraph.numberValueFormatter.call(this, x, opts);
};

/**
 * @type {!Array.<string>}
 * @private
 * @constant
 */
Dygraph.SHORT_MONTH_NAMES_ = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];


/**
 * Convert a JS date to a string appropriate to display on an axis that
 * is displaying values at the stated granularity. This respects the 
 * labelsUTC option.
 * @param {Date} date The date to format
 * @param {number} granularity One of the Dygraph granularity constants
 * @param {Dygraph} opts An options view
 * @return {string} The date formatted as local time
 * @private
 */
Dygraph.dateAxisLabelFormatter = function(date, granularity, opts) {
  var utc = opts('labelsUTC');
  var accessors = utc ? Dygraph.DateAccessorsUTC : Dygraph.DateAccessorsLocal;

  var year = accessors.getFullYear(date),
      month = accessors.getMonth(date),
      day = accessors.getDate(date),
      hours = accessors.getHours(date),
      mins = accessors.getMinutes(date),
      secs = accessors.getSeconds(date),
      millis = accessors.getSeconds(date);

  if (granularity >= Dygraph.DECADAL) {
    return '' + year;
  } else if (granularity >= Dygraph.MONTHLY) {
    return Dygraph.SHORT_MONTH_NAMES_[month] + '&#160;' + year;
  } else {
    var frac = hours * 3600 + mins * 60 + secs + 1e-3 * millis;
    if (frac === 0 || granularity >= Dygraph.DAILY) {
      // e.g. '21 Jan' (%d%b)
      return Dygraph.zeropad(day) + '&#160;' + Dygraph.SHORT_MONTH_NAMES_[month];
    } else {
      return Dygraph.hmsString_(hours, mins, secs);
    }
  }
};
// alias in case anyone is referencing the old method.
Dygraph.dateAxisFormatter = Dygraph.dateAxisLabelFormatter;

/**
 * Return a string version of a JS date for a value label. This respects the 
 * labelsUTC option.
 * @param {Date} date The date to be formatted
 * @param {Dygraph} opts An options view
 * @private
 */
Dygraph.dateValueFormatter = function(d, opts) {
  return Dygraph.dateString_(d, opts('labelsUTC'));
};

/**
 * Standard plotters. These may be used by clients.
 * Available plotters are:
 * - Dygraph.Plotters.linePlotter: draws central lines (most common)
 * - Dygraph.Plotters.errorPlotter: draws error bars
 * - Dygraph.Plotters.fillPlotter: draws fills under lines (used with fillGraph)
 *
 * By default, the plotter is [fillPlotter, errorPlotter, linePlotter].
 * This causes all the lines to be drawn over all the fills/error bars.
 */
Dygraph.Plotters = DygraphCanvasRenderer._Plotters;


// Default attribute values.
Dygraph.DEFAULT_ATTRS = {
  highlightCircleSize: 3,
  highlightSeriesOpts: null,
  highlightSeriesBackgroundAlpha: 0.5,

  labelsDivWidth: 250,
  labelsDivStyles: {
    // TODO(danvk): move defaults from createStatusMessage_ here.
  },
  labelsSeparateLines: false,
  labelsShowZeroValues: true,
  labelsKMB: false,
  labelsKMG2: false,
  showLabelsOnHighlight: true,

  digitsAfterDecimal: 2,
  maxNumberWidth: 6,
  sigFigs: null,

  strokeWidth: 1.0,
  strokeBorderWidth: 0,
  strokeBorderColor: "white",

  axisTickSize: 3,
  axisLabelFontSize: 14,
  rightGap: 5,

  showRoller: false,
  xValueParser: Dygraph.dateParser,

  delimiter: ',',

  sigma: 2.0,
  errorBars: false,
  fractions: false,
  wilsonInterval: true,  // only relevant if fractions is true
  customBars: false,
  fillGraph: false,
  fillAlpha: 0.15,
  connectSeparatedPoints: false,

  stackedGraph: false,
  stackedGraphNaNFill: 'all',
  hideOverlayOnMouseOut: true,

  legend: 'onmouseover',
  stepPlot: false,
  avoidMinZero: false,
  xRangePad: 0,
  yRangePad: null,
  drawAxesAtZero: false,

  // Sizes of the various chart labels.
  titleHeight: 28,
  xLabelHeight: 18,
  yLabelWidth: 18,

  drawXAxis: true,
  drawYAxis: true,
  axisLineColor: "black",
  axisLineWidth: 0.3,
  gridLineWidth: 0.3,
  axisLabelColor: "black",
  axisLabelWidth: 50,
  drawYGrid: true,
  drawXGrid: true,
  gridLineColor: "rgb(128,128,128)",

  interactionModel: null,  // will be set to Dygraph.Interaction.defaultModel
  animatedZooms: false,  // (for now)

  // Range selector options
  showRangeSelector: false,
  rangeSelectorHeight: 40,
  rangeSelectorPlotStrokeColor: "#808FAB",
  rangeSelectorPlotFillColor: "#A7B1C4",
  showInRangeSelector: null,

  // The ordering here ensures that central lines always appear above any
  // fill bars/error bars.
  plotter: [
    Dygraph.Plotters.fillPlotter,
    Dygraph.Plotters.errorPlotter,
    Dygraph.Plotters.linePlotter
  ],

  plugins: [ ],

  // per-axis options
  axes: {
    x: {
      pixelsPerLabel: 70,
      axisLabelWidth: 60,
      axisLabelFormatter: Dygraph.dateAxisLabelFormatter,
      valueFormatter: Dygraph.dateValueFormatter,
      drawGrid: true,
      drawAxis: true,
      independentTicks: true,
      ticker: null  // will be set in dygraph-tickers.js
    },
    y: {
      axisLabelWidth: 50,
      pixelsPerLabel: 30,
      valueFormatter: Dygraph.numberValueFormatter,
      axisLabelFormatter: Dygraph.numberAxisLabelFormatter,
      drawGrid: true,
      drawAxis: true,
      independentTicks: true,
      ticker: null  // will be set in dygraph-tickers.js
    },
    y2: {
      axisLabelWidth: 50,
      pixelsPerLabel: 30,
      valueFormatter: Dygraph.numberValueFormatter,
      axisLabelFormatter: Dygraph.numberAxisLabelFormatter,
      drawAxis: true,  // only applies when there are two axes of data.
      drawGrid: false,
      independentTicks: false,
      ticker: null  // will be set in dygraph-tickers.js
    }
  }
};

// Directions for panning and zooming. Use bit operations when combined
// values are possible.
Dygraph.HORIZONTAL = 1;
Dygraph.VERTICAL = 2;

// Installed plugins, in order of precedence (most-general to most-specific).
// Plugins are installed after they are defined, in plugins/install.js.
Dygraph.PLUGINS = [
];

// Used for initializing annotation CSS rules only once.
Dygraph.addedAnnotationCSS = false;

Dygraph.prototype.__old_init__ = function(div, file, labels, attrs) {
  // Labels is no longer a constructor parameter, since it's typically set
  // directly from the data source. It also conains a name for the x-axis,
  // which the previous constructor form did not.
  if (labels !== null) {
    var new_labels = ["Date"];
    for (var i = 0; i < labels.length; i++) new_labels.push(labels[i]);
    Dygraph.update(attrs, { 'labels': new_labels });
  }
  this.__init__(div, file, attrs);
};

/**
 * Initializes the Dygraph. This creates a new DIV and constructs the PlotKit
 * and context &lt;canvas&gt; inside of it. See the constructor for details.
 * on the parameters.
 * @param {Element} div the Element to render the graph into.
 * @param {string | Function} file Source data
 * @param {Object} attrs Miscellaneous other options
 * @private
 */
Dygraph.prototype.__init__ = function(div, file, attrs) {
  // Hack for IE: if we're using excanvas and the document hasn't finished
  // loading yet (and hence may not have initialized whatever it needs to
  // initialize), then keep calling this routine periodically until it has.
  if (/MSIE/.test(navigator.userAgent) && !window.opera &&
      typeof(G_vmlCanvasManager) != 'undefined' &&
      document.readyState != 'complete') {
    var self = this;
    setTimeout(function() { self.__init__(div, file, attrs); }, 100);
    return;
  }

  // Support two-argument constructor
  if (attrs === null || attrs === undefined) { attrs = {}; }

  attrs = Dygraph.mapLegacyOptions_(attrs);

  if (typeof(div) == 'string') {
    div = document.getElementById(div);
  }

  if (!div) {
    console.error("Constructing dygraph with a non-existent div!");
    return;
  }

  this.isUsingExcanvas_ = typeof(G_vmlCanvasManager) != 'undefined';

  // Copy the important bits into the object
  // TODO(danvk): most of these should just stay in the attrs_ dictionary.
  this.maindiv_ = div;
  this.file_ = file;
  this.rollPeriod_ = attrs.rollPeriod || Dygraph.DEFAULT_ROLL_PERIOD;
  this.previousVerticalX_ = -1;
  this.fractions_ = attrs.fractions || false;
  this.dateWindow_ = attrs.dateWindow || null;

  this.annotations_ = [];

  // Zoomed indicators - These indicate when the graph has been zoomed and on what axis.
  this.zoomed_x_ = false;
  this.zoomed_y_ = false;

  // Clear the div. This ensure that, if multiple dygraphs are passed the same
  // div, then only one will be drawn.
  div.innerHTML = "";

  // For historical reasons, the 'width' and 'height' options trump all CSS
  // rules _except_ for an explicit 'width' or 'height' on the div.
  // As an added convenience, if the div has zero height (like <div></div> does
  // without any styles), then we use a default height/width.
  if (div.style.width === '' && attrs.width) {
    div.style.width = attrs.width + "px";
  }
  if (div.style.height === '' && attrs.height) {
    div.style.height = attrs.height + "px";
  }
  if (div.style.height === '' && div.clientHeight === 0) {
    div.style.height = Dygraph.DEFAULT_HEIGHT + "px";
    if (div.style.width === '') {
      div.style.width = Dygraph.DEFAULT_WIDTH + "px";
    }
  }
  // These will be zero if the dygraph's div is hidden. In that case,
  // use the user-specified attributes if present. If not, use zero
  // and assume the user will call resize to fix things later.
  this.width_ = div.clientWidth || attrs.width || 0;
  this.height_ = div.clientHeight || attrs.height || 0;

  // TODO(danvk): set fillGraph to be part of attrs_ here, not user_attrs_.
  if (attrs.stackedGraph) {
    attrs.fillGraph = true;
    // TODO(nikhilk): Add any other stackedGraph checks here.
  }

  // DEPRECATION WARNING: All option processing should be moved from
  // attrs_ and user_attrs_ to options_, which holds all this information.
  //
  // Dygraphs has many options, some of which interact with one another.
  // To keep track of everything, we maintain two sets of options:
  //
  //  this.user_attrs_   only options explicitly set by the user.
  //  this.attrs_        defaults, options derived from user_attrs_, data.
  //
  // Options are then accessed this.attr_('attr'), which first looks at
  // user_attrs_ and then computed attrs_. This way Dygraphs can set intelligent
  // defaults without overriding behavior that the user specifically asks for.
  this.user_attrs_ = {};
  Dygraph.update(this.user_attrs_, attrs);

  // This sequence ensures that Dygraph.DEFAULT_ATTRS is never modified.
  this.attrs_ = {};
  Dygraph.updateDeep(this.attrs_, Dygraph.DEFAULT_ATTRS);

  this.boundaryIds_ = [];
  this.setIndexByName_ = {};
  this.datasetIndex_ = [];

  this.registeredEvents_ = [];
  this.eventListeners_ = {};

  this.attributes_ = new DygraphOptions(this);

  // Create the containing DIV and other interactive elements
  this.createInterface_();

  // Activate plugins.
  this.plugins_ = [];
  var plugins = Dygraph.PLUGINS.concat(this.getOption('plugins'));
  for (var i = 0; i < plugins.length; i++) {
    // the plugins option may contain either plugin classes or instances.
    // Plugin instances contain an activate method.
    var Plugin = plugins[i];  // either a constructor or an instance.
    var pluginInstance;
    if (typeof(Plugin.activate) !== 'undefined') {
      pluginInstance = Plugin;
    } else {
      pluginInstance = new Plugin();
    }

    var pluginDict = {
      plugin: pluginInstance,
      events: {},
      options: {},
      pluginOptions: {}
    };

    var handlers = pluginInstance.activate(this);
    for (var eventName in handlers) {
      if (!handlers.hasOwnProperty(eventName)) continue;
      // TODO(danvk): validate eventName.
      pluginDict.events[eventName] = handlers[eventName];
    }

    this.plugins_.push(pluginDict);
  }

  // At this point, plugins can no longer register event handlers.
  // Construct a map from event -> ordered list of [callback, plugin].
  for (var i = 0; i < this.plugins_.length; i++) {
    var plugin_dict = this.plugins_[i];
    for (var eventName in plugin_dict.events) {
      if (!plugin_dict.events.hasOwnProperty(eventName)) continue;
      var callback = plugin_dict.events[eventName];

      var pair = [plugin_dict.plugin, callback];
      if (!(eventName in this.eventListeners_)) {
        this.eventListeners_[eventName] = [pair];
      } else {
        this.eventListeners_[eventName].push(pair);
      }
    }
  }

  this.createDragInterface_();

  this.start_();
};

/**
 * Triggers a cascade of events to the various plugins which are interested in them.
 * Returns true if the "default behavior" should be prevented, i.e. if one
 * of the event listeners called event.preventDefault().
 * @private
 */
Dygraph.prototype.cascadeEvents_ = function(name, extra_props) {
  if (!(name in this.eventListeners_)) return false;

  // QUESTION: can we use objects & prototypes to speed this up?
  var e = {
    dygraph: this,
    cancelable: false,
    defaultPrevented: false,
    preventDefault: function() {
      if (!e.cancelable) throw "Cannot call preventDefault on non-cancelable event.";
      e.defaultPrevented = true;
    },
    propagationStopped: false,
    stopPropagation: function() {
      e.propagationStopped = true;
    }
  };
  Dygraph.update(e, extra_props);

  var callback_plugin_pairs = this.eventListeners_[name];
  if (callback_plugin_pairs) {
    for (var i = callback_plugin_pairs.length - 1; i >= 0; i--) {
      var plugin = callback_plugin_pairs[i][0];
      var callback = callback_plugin_pairs[i][1];
      callback.call(plugin, e);
      if (e.propagationStopped) break;
    }
  }
  return e.defaultPrevented;
};

/**
 * Fetch a plugin instance of a particular class. Only for testing.
 * @private
 * @param {!Class} type The type of the plugin.
 * @return {Object} Instance of the plugin, or null if there is none.
 */
Dygraph.prototype.getPluginInstance_ = function(type) {
  for (var i = 0; i < this.plugins_.length; i++) {
    var p = this.plugins_[i];
    if (p.plugin instanceof type) {
      return p.plugin;
    }
  }
  return null;
};

/**
 * Returns the zoomed status of the chart for one or both axes.
 *
 * Axis is an optional parameter. Can be set to 'x' or 'y'.
 *
 * The zoomed status for an axis is set whenever a user zooms using the mouse
 * or when the dateWindow or valueRange are updated (unless the
 * isZoomedIgnoreProgrammaticZoom option is also specified).
 */
Dygraph.prototype.isZoomed = function(axis) {
  if (axis === null || axis === undefined) {
    return this.zoomed_x_ || this.zoomed_y_;
  }
  if (axis === 'x') return this.zoomed_x_;
  if (axis === 'y') return this.zoomed_y_;
  throw "axis parameter is [" + axis + "] must be null, 'x' or 'y'.";
};

/**
 * Returns information about the Dygraph object, including its containing ID.
 */
Dygraph.prototype.toString = function() {
  var maindiv = this.maindiv_;
  var id = (maindiv && maindiv.id) ? maindiv.id : maindiv;
  return "[Dygraph " + id + "]";
};

/**
 * @private
 * Returns the value of an option. This may be set by the user (either in the
 * constructor or by calling updateOptions) or by dygraphs, and may be set to a
 * per-series value.
 * @param {string} name The name of the option, e.g. 'rollPeriod'.
 * @param {string} [seriesName] The name of the series to which the option
 * will be applied. If no per-series value of this option is available, then
 * the global value is returned. This is optional.
 * @return { ... } The value of the option.
 */
Dygraph.prototype.attr_ = function(name, seriesName) {
  if (DEBUG) {
    if (typeof(Dygraph.OPTIONS_REFERENCE) === 'undefined') {
      console.error('Must include options reference JS for testing');
    } else if (!Dygraph.OPTIONS_REFERENCE.hasOwnProperty(name)) {
      console.error('Dygraphs is using property ' + name + ', which has no ' +
                    'entry in the Dygraphs.OPTIONS_REFERENCE listing.');
      // Only log this error once.
      Dygraph.OPTIONS_REFERENCE[name] = true;
    }
  }
  return seriesName ? this.attributes_.getForSeries(name, seriesName) : this.attributes_.get(name);
};

/**
 * Returns the current value for an option, as set in the constructor or via
 * updateOptions. You may pass in an (optional) series name to get per-series
 * values for the option.
 *
 * All values returned by this method should be considered immutable. If you
 * modify them, there is no guarantee that the changes will be honored or that
 * dygraphs will remain in a consistent state. If you want to modify an option,
 * use updateOptions() instead.
 *
 * @param {string} name The name of the option (e.g. 'strokeWidth')
 * @param {string=} opt_seriesName Series name to get per-series values.
 * @return {*} The value of the option.
 */
Dygraph.prototype.getOption = function(name, opt_seriesName) {
  return this.attr_(name, opt_seriesName);
};

/**
 * Like getOption(), but specifically returns a number.
 * This is a convenience function for working with the Closure Compiler.
 * @param {string} name The name of the option (e.g. 'strokeWidth')
 * @param {string=} opt_seriesName Series name to get per-series values.
 * @return {number} The value of the option.
 * @private
 */
Dygraph.prototype.getNumericOption = function(name, opt_seriesName) {
  return /** @type{number} */(this.getOption(name, opt_seriesName));
};

/**
 * Like getOption(), but specifically returns a string.
 * This is a convenience function for working with the Closure Compiler.
 * @param {string} name The name of the option (e.g. 'strokeWidth')
 * @param {string=} opt_seriesName Series name to get per-series values.
 * @return {string} The value of the option.
 * @private
 */
Dygraph.prototype.getStringOption = function(name, opt_seriesName) {
  return /** @type{string} */(this.getOption(name, opt_seriesName));
};

/**
 * Like getOption(), but specifically returns a boolean.
 * This is a convenience function for working with the Closure Compiler.
 * @param {string} name The name of the option (e.g. 'strokeWidth')
 * @param {string=} opt_seriesName Series name to get per-series values.
 * @return {boolean} The value of the option.
 * @private
 */
Dygraph.prototype.getBooleanOption = function(name, opt_seriesName) {
  return /** @type{boolean} */(this.getOption(name, opt_seriesName));
};

/**
 * Like getOption(), but specifically returns a function.
 * This is a convenience function for working with the Closure Compiler.
 * @param {string} name The name of the option (e.g. 'strokeWidth')
 * @param {string=} opt_seriesName Series name to get per-series values.
 * @return {function(...)} The value of the option.
 * @private
 */
Dygraph.prototype.getFunctionOption = function(name, opt_seriesName) {
  return /** @type{function(...)} */(this.getOption(name, opt_seriesName));
};

Dygraph.prototype.getOptionForAxis = function(name, axis) {
  return this.attributes_.getForAxis(name, axis);
};

/**
 * @private
 * @param {string} axis The name of the axis (i.e. 'x', 'y' or 'y2')
 * @return { ... } A function mapping string -> option value
 */
Dygraph.prototype.optionsViewForAxis_ = function(axis) {
  var self = this;
  return function(opt) {
    var axis_opts = self.user_attrs_.axes;
    if (axis_opts && axis_opts[axis] && axis_opts[axis].hasOwnProperty(opt)) {
      return axis_opts[axis][opt];
    }

    // I don't like that this is in a second spot.
    if (axis === 'x' && opt === 'logscale') {
      // return the default value.
      // TODO(konigsberg): pull the default from a global default.
      return false;
    }

    // user-specified attributes always trump defaults, even if they're less
    // specific.
    if (typeof(self.user_attrs_[opt]) != 'undefined') {
      return self.user_attrs_[opt];
    }

    axis_opts = self.attrs_.axes;
    if (axis_opts && axis_opts[axis] && axis_opts[axis].hasOwnProperty(opt)) {
      return axis_opts[axis][opt];
    }
    // check old-style axis options
    // TODO(danvk): add a deprecation warning if either of these match.
    if (axis == 'y' && self.axes_[0].hasOwnProperty(opt)) {
      return self.axes_[0][opt];
    } else if (axis == 'y2' && self.axes_[1].hasOwnProperty(opt)) {
      return self.axes_[1][opt];
    }
    return self.attr_(opt);
  };
};

/**
 * Returns the current rolling period, as set by the user or an option.
 * @return {number} The number of points in the rolling window
 */
Dygraph.prototype.rollPeriod = function() {
  return this.rollPeriod_;
};

/**
 * Returns the currently-visible x-range. This can be affected by zooming,
 * panning or a call to updateOptions.
 * Returns a two-element array: [left, right].
 * If the Dygraph has dates on the x-axis, these will be millis since epoch.
 */
Dygraph.prototype.xAxisRange = function() {
  return this.dateWindow_ ? this.dateWindow_ : this.xAxisExtremes();
};

/**
 * Returns the lower- and upper-bound x-axis values of the
 * data set.
 */
Dygraph.prototype.xAxisExtremes = function() {
  var pad = this.getNumericOption('xRangePad') / this.plotter_.area.w;
  if (this.numRows() === 0) {
    return [0 - pad, 1 + pad];
  }
  var left = this.rawData_[0][0];
  var right = this.rawData_[this.rawData_.length - 1][0];
  if (pad) {
    // Must keep this in sync with dygraph-layout _evaluateLimits()
    var range = right - left;
    left -= range * pad;
    right += range * pad;
  }
  return [left, right];
};

/**
 * Returns the currently-visible y-range for an axis. This can be affected by
 * zooming, panning or a call to updateOptions. Axis indices are zero-based. If
 * called with no arguments, returns the range of the first axis.
 * Returns a two-element array: [bottom, top].
 */
Dygraph.prototype.yAxisRange = function(idx) {
  if (typeof(idx) == "undefined") idx = 0;
  if (idx < 0 || idx >= this.axes_.length) {
    return null;
  }
  var axis = this.axes_[idx];
  return [ axis.computedValueRange[0], axis.computedValueRange[1] ];
};

/**
 * Returns the currently-visible y-ranges for each axis. This can be affected by
 * zooming, panning, calls to updateOptions, etc.
 * Returns an array of [bottom, top] pairs, one for each y-axis.
 */
Dygraph.prototype.yAxisRanges = function() {
  var ret = [];
  for (var i = 0; i < this.axes_.length; i++) {
    ret.push(this.yAxisRange(i));
  }
  return ret;
};

// TODO(danvk): use these functions throughout dygraphs.
/**
 * Convert from data coordinates to canvas/div X/Y coordinates.
 * If specified, do this conversion for the coordinate system of a particular
 * axis. Uses the first axis by default.
 * Returns a two-element array: [X, Y]
 *
 * Note: use toDomXCoord instead of toDomCoords(x, null) and use toDomYCoord
 * instead of toDomCoords(null, y, axis).
 */
Dygraph.prototype.toDomCoords = function(x, y, axis) {
  return [ this.toDomXCoord(x), this.toDomYCoord(y, axis) ];
};

/**
 * Convert from data x coordinates to canvas/div X coordinate.
 * If specified, do this conversion for the coordinate system of a particular
 * axis.
 * Returns a single value or null if x is null.
 */
Dygraph.prototype.toDomXCoord = function(x) {
  if (x === null) {
    return null;
  }

  var area = this.plotter_.area;
  var xRange = this.xAxisRange();
  return area.x + (x - xRange[0]) / (xRange[1] - xRange[0]) * area.w;
};

/**
 * Convert from data x coordinates to canvas/div Y coordinate and optional
 * axis. Uses the first axis by default.
 *
 * returns a single value or null if y is null.
 */
Dygraph.prototype.toDomYCoord = function(y, axis) {
  var pct = this.toPercentYCoord(y, axis);

  if (pct === null) {
    return null;
  }
  var area = this.plotter_.area;
  return area.y + pct * area.h;
};

/**
 * Convert from canvas/div coords to data coordinates.
 * If specified, do this conversion for the coordinate system of a particular
 * axis. Uses the first axis by default.
 * Returns a two-element array: [X, Y].
 *
 * Note: use toDataXCoord instead of toDataCoords(x, null) and use toDataYCoord
 * instead of toDataCoords(null, y, axis).
 */
Dygraph.prototype.toDataCoords = function(x, y, axis) {
  return [ this.toDataXCoord(x), this.toDataYCoord(y, axis) ];
};

/**
 * Convert from canvas/div x coordinate to data coordinate.
 *
 * If x is null, this returns null.
 */
Dygraph.prototype.toDataXCoord = function(x) {
  if (x === null) {
    return null;
  }

  var area = this.plotter_.area;
  var xRange = this.xAxisRange();

  if (!this.attributes_.getForAxis("logscale", 'x')) {
    return xRange[0] + (x - area.x) / area.w * (xRange[1] - xRange[0]);
  } else {
    // TODO: remove duplicate code?
    // Computing the inverse of toDomCoord.
    var pct = (x - area.x) / area.w;

    // Computing the inverse of toPercentXCoord. The function was arrived at with
    // the following steps:
    //
    // Original calcuation:
    // pct = (log(x) - log(xRange[0])) / (log(xRange[1]) - log(xRange[0])));
    //
    // Multiply both sides by the right-side demoninator.
    // pct * (log(xRange[1] - log(xRange[0]))) = log(x) - log(xRange[0])
    //
    // add log(xRange[0]) to both sides
    // log(xRange[0]) + (pct * (log(xRange[1]) - log(xRange[0])) = log(x);
    //
    // Swap both sides of the equation,
    // log(x) = log(xRange[0]) + (pct * (log(xRange[1]) - log(xRange[0]))
    //
    // Use both sides as the exponent in 10^exp and we're done.
    // x = 10 ^ (log(xRange[0]) + (pct * (log(xRange[1]) - log(xRange[0])))
    var logr0 = Dygraph.log10(xRange[0]);
    var logr1 = Dygraph.log10(xRange[1]);
    var exponent = logr0 + (pct * (logr1 - logr0));
    var value = Math.pow(Dygraph.LOG_SCALE, exponent);
    return value;
  }
};

/**
 * Convert from canvas/div y coord to value.
 *
 * If y is null, this returns null.
 * if axis is null, this uses the first axis.
 */
Dygraph.prototype.toDataYCoord = function(y, axis) {
  if (y === null) {
    return null;
  }

  var area = this.plotter_.area;
  var yRange = this.yAxisRange(axis);

  if (typeof(axis) == "undefined") axis = 0;
  if (!this.attributes_.getForAxis("logscale", axis)) {
    return yRange[0] + (area.y + area.h - y) / area.h * (yRange[1] - yRange[0]);
  } else {
    // Computing the inverse of toDomCoord.
    var pct = (y - area.y) / area.h;

    // Computing the inverse of toPercentYCoord. The function was arrived at with
    // the following steps:
    //
    // Original calcuation:
    // pct = (log(yRange[1]) - log(y)) / (log(yRange[1]) - log(yRange[0]));
    //
    // Multiply both sides by the right-side demoninator.
    // pct * (log(yRange[1]) - log(yRange[0])) = log(yRange[1]) - log(y);
    //
    // subtract log(yRange[1]) from both sides.
    // (pct * (log(yRange[1]) - log(yRange[0]))) - log(yRange[1]) = -log(y);
    //
    // and multiply both sides by -1.
    // log(yRange[1]) - (pct * (logr1 - log(yRange[0])) = log(y);
    //
    // Swap both sides of the equation,
    // log(y) = log(yRange[1]) - (pct * (log(yRange[1]) - log(yRange[0])));
    //
    // Use both sides as the exponent in 10^exp and we're done.
    // y = 10 ^ (log(yRange[1]) - (pct * (log(yRange[1]) - log(yRange[0]))));
    var logr0 = Dygraph.log10(yRange[0]);
    var logr1 = Dygraph.log10(yRange[1]);
    var exponent = logr1 - (pct * (logr1 - logr0));
    var value = Math.pow(Dygraph.LOG_SCALE, exponent);
    return value;
  }
};

/**
 * Converts a y for an axis to a percentage from the top to the
 * bottom of the drawing area.
 *
 * If the coordinate represents a value visible on the canvas, then
 * the value will be between 0 and 1, where 0 is the top of the canvas.
 * However, this method will return values outside the range, as
 * values can fall outside the canvas.
 *
 * If y is null, this returns null.
 * if axis is null, this uses the first axis.
 *
 * @param {number} y The data y-coordinate.
 * @param {number} [axis] The axis number on which the data coordinate lives.
 * @return {number} A fraction in [0, 1] where 0 = the top edge.
 */
Dygraph.prototype.toPercentYCoord = function(y, axis) {
  if (y === null) {
    return null;
  }
  if (typeof(axis) == "undefined") axis = 0;

  var yRange = this.yAxisRange(axis);

  var pct;
  var logscale = this.attributes_.getForAxis("logscale", axis);
  if (logscale) {
    var logr0 = Dygraph.log10(yRange[0]);
    var logr1 = Dygraph.log10(yRange[1]);
    pct = (logr1 - Dygraph.log10(y)) / (logr1 - logr0);
  } else {
    // yRange[1] - y is unit distance from the bottom.
    // yRange[1] - yRange[0] is the scale of the range.
    // (yRange[1] - y) / (yRange[1] - yRange[0]) is the % from the bottom.
    pct = (yRange[1] - y) / (yRange[1] - yRange[0]);
  }
  return pct;
};

/**
 * Converts an x value to a percentage from the left to the right of
 * the drawing area.
 *
 * If the coordinate represents a value visible on the canvas, then
 * the value will be between 0 and 1, where 0 is the left of the canvas.
 * However, this method will return values outside the range, as
 * values can fall outside the canvas.
 *
 * If x is null, this returns null.
 * @param {number} x The data x-coordinate.
 * @return {number} A fraction in [0, 1] where 0 = the left edge.
 */
Dygraph.prototype.toPercentXCoord = function(x) {
  if (x === null) {
    return null;
  }

  var xRange = this.xAxisRange();
  var pct;
  var logscale = this.attributes_.getForAxis("logscale", 'x') ;
  if (logscale === true) {  // logscale can be null so we test for true explicitly.
    var logr0 = Dygraph.log10(xRange[0]);
    var logr1 = Dygraph.log10(xRange[1]);
    pct = (Dygraph.log10(x) - logr0) / (logr1 - logr0);
  } else {
    // x - xRange[0] is unit distance from the left.
    // xRange[1] - xRange[0] is the scale of the range.
    // The full expression below is the % from the left.
    pct = (x - xRange[0]) / (xRange[1] - xRange[0]);
  }
  return pct;
};

/**
 * Returns the number of columns (including the independent variable).
 * @return {number} The number of columns.
 */
Dygraph.prototype.numColumns = function() {
  if (!this.rawData_) return 0;
  return this.rawData_[0] ? this.rawData_[0].length : this.attr_("labels").length;
};

/**
 * Returns the number of rows (excluding any header/label row).
 * @return {number} The number of rows, less any header.
 */
Dygraph.prototype.numRows = function() {
  if (!this.rawData_) return 0;
  return this.rawData_.length;
};

/**
 * Returns the value in the given row and column. If the row and column exceed
 * the bounds on the data, returns null. Also returns null if the value is
 * missing.
 * @param {number} row The row number of the data (0-based). Row 0 is the
 *     first row of data, not a header row.
 * @param {number} col The column number of the data (0-based)
 * @return {number} The value in the specified cell or null if the row/col
 *     were out of range.
 */
Dygraph.prototype.getValue = function(row, col) {
  if (row < 0 || row > this.rawData_.length) return null;
  if (col < 0 || col > this.rawData_[row].length) return null;

  return this.rawData_[row][col];
};

/**
 * Generates interface elements for the Dygraph: a containing div, a div to
 * display the current point, and a textbox to adjust the rolling average
 * period. Also creates the Renderer/Layout elements.
 * @private
 */
Dygraph.prototype.createInterface_ = function() {
  // Create the all-enclosing graph div
  var enclosing = this.maindiv_;

  this.graphDiv = document.createElement("div");

  // TODO(danvk): any other styles that are useful to set here?
  this.graphDiv.style.textAlign = 'left';  // This is a CSS "reset"
  this.graphDiv.style.position = 'relative';
  enclosing.appendChild(this.graphDiv);

  // Create the canvas for interactive parts of the chart.
  this.canvas_ = Dygraph.createCanvas();
  this.canvas_.style.position = "absolute";

  // ... and for static parts of the chart.
  this.hidden_ = this.createPlotKitCanvas_(this.canvas_);

  this.canvas_ctx_ = Dygraph.getContext(this.canvas_);
  this.hidden_ctx_ = Dygraph.getContext(this.hidden_);

  this.resizeElements_();

  // The interactive parts of the graph are drawn on top of the chart.
  this.graphDiv.appendChild(this.hidden_);
  this.graphDiv.appendChild(this.canvas_);
  this.mouseEventElement_ = this.createMouseEventElement_();

  // Create the grapher
  this.layout_ = new DygraphLayout(this);

  var dygraph = this;

  this.mouseMoveHandler_ = function(e) {
    dygraph.mouseMove_(e);
  };

  this.mouseOutHandler_ = function(e) {
    // The mouse has left the chart if:
    // 1. e.target is inside the chart
    // 2. e.relatedTarget is outside the chart
    var target = e.target || e.fromElement;
    var relatedTarget = e.relatedTarget || e.toElement;
    if (Dygraph.isNodeContainedBy(target, dygraph.graphDiv) &&
        !Dygraph.isNodeContainedBy(relatedTarget, dygraph.graphDiv)) {
      dygraph.mouseOut_(e);
    }
  };

  this.addAndTrackEvent(window, 'mouseout', this.mouseOutHandler_);
  this.addAndTrackEvent(this.mouseEventElement_, 'mousemove', this.mouseMoveHandler_);

  // Don't recreate and register the resize handler on subsequent calls.
  // This happens when the graph is resized.
  if (!this.resizeHandler_) {
    this.resizeHandler_ = function(e) {
      dygraph.resize();
    };

    // Update when the window is resized.
    // TODO(danvk): drop frames depending on complexity of the chart.
    this.addAndTrackEvent(window, 'resize', this.resizeHandler_);
  }
};

Dygraph.prototype.resizeElements_ = function() {
  this.graphDiv.style.width = this.width_ + "px";
  this.graphDiv.style.height = this.height_ + "px";

  var canvasScale = Dygraph.getContextPixelRatio(this.canvas_ctx_);
  this.canvas_.width = this.width_ * canvasScale;
  this.canvas_.height = this.height_ * canvasScale;
  this.canvas_.style.width = this.width_ + "px";    // for IE
  this.canvas_.style.height = this.height_ + "px";  // for IE
  if (canvasScale !== 1) {
    this.canvas_ctx_.scale(canvasScale, canvasScale);
  }

  var hiddenScale = Dygraph.getContextPixelRatio(this.hidden_ctx_);
  this.hidden_.width = this.width_ * hiddenScale;
  this.hidden_.height = this.height_ * hiddenScale;
  this.hidden_.style.width = this.width_ + "px";    // for IE
  this.hidden_.style.height = this.height_ + "px";  // for IE
  if (hiddenScale !== 1) {
    this.hidden_ctx_.scale(hiddenScale, hiddenScale);
  }
};

/**
 * Detach DOM elements in the dygraph and null out all data references.
 * Calling this when you're done with a dygraph can dramatically reduce memory
 * usage. See, e.g., the tests/perf.html example.
 */
Dygraph.prototype.destroy = function() {
  this.canvas_ctx_.restore();
  this.hidden_ctx_.restore();

  // Destroy any plugins, in the reverse order that they were registered.
  for (var i = this.plugins_.length - 1; i >= 0; i--) {
    var p = this.plugins_.pop();
    if (p.plugin.destroy) p.plugin.destroy();
  }

  var removeRecursive = function(node) {
    while (node.hasChildNodes()) {
      removeRecursive(node.firstChild);
      node.removeChild(node.firstChild);
    }
  };

  this.removeTrackedEvents_();

  // remove mouse event handlers (This may not be necessary anymore)
  Dygraph.removeEvent(window, 'mouseout', this.mouseOutHandler_);
  Dygraph.removeEvent(this.mouseEventElement_, 'mousemove', this.mouseMoveHandler_);

  // remove window handlers
  Dygraph.removeEvent(window,'resize', this.resizeHandler_);
  this.resizeHandler_ = null;

  removeRecursive(this.maindiv_);

  var nullOut = function(obj) {
    for (var n in obj) {
      if (typeof(obj[n]) === 'object') {
        obj[n] = null;
      }
    }
  };
  // These may not all be necessary, but it can't hurt...
  nullOut(this.layout_);
  nullOut(this.plotter_);
  nullOut(this);
};

/**
 * Creates the canvas on which the chart will be drawn. Only the Renderer ever
 * draws on this particular canvas. All Dygraph work (i.e. drawing hover dots
 * or the zoom rectangles) is done on this.canvas_.
 * @param {Object} canvas The Dygraph canvas over which to overlay the plot
 * @return {Object} The newly-created canvas
 * @private
 */
Dygraph.prototype.createPlotKitCanvas_ = function(canvas) {
  var h = Dygraph.createCanvas();
  h.style.position = "absolute";
  // TODO(danvk): h should be offset from canvas. canvas needs to include
  // some extra area to make it easier to zoom in on the far left and far
  // right. h needs to be precisely the plot area, so that clipping occurs.
  h.style.top = canvas.style.top;
  h.style.left = canvas.style.left;
  h.width = this.width_;
  h.height = this.height_;
  h.style.width = this.width_ + "px";    // for IE
  h.style.height = this.height_ + "px";  // for IE
  return h;
};

/**
 * Creates an overlay element used to handle mouse events.
 * @return {Object} The mouse event element.
 * @private
 */
Dygraph.prototype.createMouseEventElement_ = function() {
  if (this.isUsingExcanvas_) {
    var elem = document.createElement("div");
    elem.style.position = 'absolute';
    elem.style.backgroundColor = 'white';
    elem.style.filter = 'alpha(opacity=0)';
    elem.style.width = this.width_ + "px";
    elem.style.height = this.height_ + "px";
    this.graphDiv.appendChild(elem);
    return elem;
  } else {
    return this.canvas_;
  }
};

/**
 * Generate a set of distinct colors for the data series. This is done with a
 * color wheel. Saturation/Value are customizable, and the hue is
 * equally-spaced around the color wheel. If a custom set of colors is
 * specified, that is used instead.
 * @private
 */
Dygraph.prototype.setColors_ = function() {
  var labels = this.getLabels();
  var num = labels.length - 1;
  this.colors_ = [];
  this.colorsMap_ = {};

  // These are used for when no custom colors are specified.
  var sat = this.getNumericOption('colorSaturation') || 1.0;
  var val = this.getNumericOption('colorValue') || 0.5;
  var half = Math.ceil(num / 2);

  var colors = this.getOption('colors');
  var visibility = this.visibility();
  for (var i = 0; i < num; i++) {
    if (!visibility[i]) {
      continue;
    }
    var label = labels[i + 1];
    var colorStr = this.attributes_.getForSeries('color', label);
    if (!colorStr) {
      if (colors) {
        colorStr = colors[i % colors.length];
      } else {
        // alternate colors for high contrast.
        var idx = i % 2 ? (half + (i + 1)/ 2) : Math.ceil((i + 1) / 2);
        var hue = (1.0 * idx / (1 + num));
        colorStr = Dygraph.hsvToRGB(hue, sat, val);
      }
    }
    this.colors_.push(colorStr);
    this.colorsMap_[label] = colorStr;
  }
};

/**
 * Return the list of colors. This is either the list of colors passed in the
 * attributes or the autogenerated list of rgb(r,g,b) strings.
 * This does not return colors for invisible series.
 * @return {Array.<string>} The list of colors.
 */
Dygraph.prototype.getColors = function() {
  return this.colors_;
};

/**
 * Returns a few attributes of a series, i.e. its color, its visibility, which
 * axis it's assigned to, and its column in the original data.
 * Returns null if the series does not exist.
 * Otherwise, returns an object with column, visibility, color and axis properties.
 * The "axis" property will be set to 1 for y1 and 2 for y2.
 * The "column" property can be fed back into getValue(row, column) to get
 * values for this series.
 */
Dygraph.prototype.getPropertiesForSeries = function(series_name) {
  var idx = -1;
  var labels = this.getLabels();
  for (var i = 1; i < labels.length; i++) {
    if (labels[i] == series_name) {
      idx = i;
      break;
    }
  }
  if (idx == -1) return null;

  return {
    name: series_name,
    column: idx,
    visible: this.visibility()[idx - 1],
    color: this.colorsMap_[series_name],
    axis: 1 + this.attributes_.axisForSeries(series_name)
  };
};

/**
 * Create the text box to adjust the averaging period
 * @private
 */
Dygraph.prototype.createRollInterface_ = function() {
  // Create a roller if one doesn't exist already.
  if (!this.roller_) {
    this.roller_ = document.createElement("input");
    this.roller_.type = "text";
    this.roller_.style.display = "none";
    this.graphDiv.appendChild(this.roller_);
  }

  var display = this.getBooleanOption('showRoller') ? 'block' : 'none';

  var area = this.plotter_.area;
  var textAttr = { "position": "absolute",
                   "zIndex": 10,
                   "top": (area.y + area.h - 25) + "px",
                   "left": (area.x + 1) + "px",
                   "display": display
                  };
  this.roller_.size = "2";
  this.roller_.value = this.rollPeriod_;
  for (var name in textAttr) {
    if (textAttr.hasOwnProperty(name)) {
      this.roller_.style[name] = textAttr[name];
    }
  }

  var dygraph = this;
  this.roller_.onchange = function() { dygraph.adjustRoll(dygraph.roller_.value); };
};

/**
 * Set up all the mouse handlers needed to capture dragging behavior for zoom
 * events.
 * @private
 */
Dygraph.prototype.createDragInterface_ = function() {
  var context = {
    // Tracks whether the mouse is down right now
    isZooming: false,
    isPanning: false,  // is this drag part of a pan?
    is2DPan: false,    // if so, is that pan 1- or 2-dimensional?
    dragStartX: null, // pixel coordinates
    dragStartY: null, // pixel coordinates
    dragEndX: null, // pixel coordinates
    dragEndY: null, // pixel coordinates
    dragDirection: null,
    prevEndX: null, // pixel coordinates
    prevEndY: null, // pixel coordinates
    prevDragDirection: null,
    cancelNextDblclick: false,  // see comment in dygraph-interaction-model.js

    // The value on the left side of the graph when a pan operation starts.
    initialLeftmostDate: null,

    // The number of units each pixel spans. (This won't be valid for log
    // scales)
    xUnitsPerPixel: null,

    // TODO(danvk): update this comment
    // The range in second/value units that the viewport encompasses during a
    // panning operation.
    dateRange: null,

    // Top-left corner of the canvas, in DOM coords
    // TODO(konigsberg): Rename topLeftCanvasX, topLeftCanvasY.
    px: 0,
    py: 0,

    // Values for use with panEdgeFraction, which limit how far outside the
    // graph's data boundaries it can be panned.
    boundedDates: null, // [minDate, maxDate]
    boundedValues: null, // [[minValue, maxValue] ...]

    // We cover iframes during mouse interactions. See comments in
    // dygraph-utils.js for more info on why this is a good idea.
    tarp: new Dygraph.IFrameTarp(),

    // contextB is the same thing as this context object but renamed.
    initializeMouseDown: function(event, g, contextB) {
      // prevents mouse drags from selecting page text.
      if (event.preventDefault) {
        event.preventDefault();  // Firefox, Chrome, etc.
      } else {
        event.returnValue = false;  // IE
        event.cancelBubble = true;
      }

      var canvasPos = Dygraph.findPos(g.canvas_);
      contextB.px = canvasPos.x;
      contextB.py = canvasPos.y;
      contextB.dragStartX = Dygraph.dragGetX_(event, contextB);
      contextB.dragStartY = Dygraph.dragGetY_(event, contextB);
      contextB.cancelNextDblclick = false;
      contextB.tarp.cover();
    },
    destroy: function() {
      var context = this;
      if (context.isZooming || context.isPanning) {
        context.isZooming = false;
        context.dragStartX = null;
        context.dragStartY = null;
      }

      if (context.isPanning) {
        context.isPanning = false;
        context.draggingDate = null;
        context.dateRange = null;
        for (var i = 0; i < self.axes_.length; i++) {
          delete self.axes_[i].draggingValue;
          delete self.axes_[i].dragValueRange;
        }
      }

      context.tarp.uncover();
    }
  };

  var interactionModel = this.getOption("interactionModel");

  // Self is the graph.
  var self = this;

  // Function that binds the graph and context to the handler.
  var bindHandler = function(handler) {
    return function(event) {
      handler(event, self, context);
    };
  };

  for (var eventName in interactionModel) {
    if (!interactionModel.hasOwnProperty(eventName)) continue;
    this.addAndTrackEvent(this.mouseEventElement_, eventName,
        bindHandler(interactionModel[eventName]));
  }

  // If the user releases the mouse button during a drag, but not over the
  // canvas, then it doesn't count as a zooming action.
  if (!interactionModel.willDestroyContextMyself) {
    var mouseUpHandler = function(event) {
      context.destroy();
    };

    this.addAndTrackEvent(document, 'mouseup', mouseUpHandler);
  }
};

/**
 * Draw a gray zoom rectangle over the desired area of the canvas. Also clears
 * up any previous zoom rectangles that were drawn. This could be optimized to
 * avoid extra redrawing, but it's tricky to avoid interactions with the status
 * dots.
 *
 * @param {number} direction the direction of the zoom rectangle. Acceptable
 *     values are Dygraph.HORIZONTAL and Dygraph.VERTICAL.
 * @param {number} startX The X position where the drag started, in canvas
 *     coordinates.
 * @param {number} endX The current X position of the drag, in canvas coords.
 * @param {number} startY The Y position where the drag started, in canvas
 *     coordinates.
 * @param {number} endY The current Y position of the drag, in canvas coords.
 * @param {number} prevDirection the value of direction on the previous call to
 *     this function. Used to avoid excess redrawing
 * @param {number} prevEndX The value of endX on the previous call to this
 *     function. Used to avoid excess redrawing
 * @param {number} prevEndY The value of endY on the previous call to this
 *     function. Used to avoid excess redrawing
 * @private
 */
Dygraph.prototype.drawZoomRect_ = function(direction, startX, endX, startY,
                                           endY, prevDirection, prevEndX,
                                           prevEndY) {
  var ctx = this.canvas_ctx_;

  // Clean up from the previous rect if necessary
  if (prevDirection == Dygraph.HORIZONTAL) {
    ctx.clearRect(Math.min(startX, prevEndX), this.layout_.getPlotArea().y,
                  Math.abs(startX - prevEndX), this.layout_.getPlotArea().h);
  } else if (prevDirection == Dygraph.VERTICAL) {
    ctx.clearRect(this.layout_.getPlotArea().x, Math.min(startY, prevEndY),
                  this.layout_.getPlotArea().w, Math.abs(startY - prevEndY));
  }

  // Draw a light-grey rectangle to show the new viewing area
  if (direction == Dygraph.HORIZONTAL) {
    if (endX && startX) {
      ctx.fillStyle = "rgba(128,128,128,0.33)";
      ctx.fillRect(Math.min(startX, endX), this.layout_.getPlotArea().y,
                   Math.abs(endX - startX), this.layout_.getPlotArea().h);
    }
  } else if (direction == Dygraph.VERTICAL) {
    if (endY && startY) {
      ctx.fillStyle = "rgba(128,128,128,0.33)";
      ctx.fillRect(this.layout_.getPlotArea().x, Math.min(startY, endY),
                   this.layout_.getPlotArea().w, Math.abs(endY - startY));
    }
  }

  if (this.isUsingExcanvas_) {
    this.currentZoomRectArgs_ = [direction, startX, endX, startY, endY, 0, 0, 0];
  }
};

/**
 * Clear the zoom rectangle (and perform no zoom).
 * @private
 */
Dygraph.prototype.clearZoomRect_ = function() {
  this.currentZoomRectArgs_ = null;
  this.canvas_ctx_.clearRect(0, 0, this.width_, this.height_);
};

/**
 * Zoom to something containing [lowX, highX]. These are pixel coordinates in
 * the canvas. The exact zoom window may be slightly larger if there are no data
 * points near lowX or highX. Don't confuse this function with doZoomXDates,
 * which accepts dates that match the raw data. This function redraws the graph.
 *
 * @param {number} lowX The leftmost pixel value that should be visible.
 * @param {number} highX The rightmost pixel value that should be visible.
 * @private
 */
Dygraph.prototype.doZoomX_ = function(lowX, highX) {
  this.currentZoomRectArgs_ = null;
  // Find the earliest and latest dates contained in this canvasx range.
  // Convert the call to date ranges of the raw data.
  var minDate = this.toDataXCoord(lowX);
  var maxDate = this.toDataXCoord(highX);
  this.doZoomXDates_(minDate, maxDate);
};

/**
 * Zoom to something containing [minDate, maxDate] values. Don't confuse this
 * method with doZoomX which accepts pixel coordinates. This function redraws
 * the graph.
 *
 * @param {number} minDate The minimum date that should be visible.
 * @param {number} maxDate The maximum date that should be visible.
 * @private
 */
Dygraph.prototype.doZoomXDates_ = function(minDate, maxDate) {
  // TODO(danvk): when xAxisRange is null (i.e. "fit to data", the animation
  // can produce strange effects. Rather than the x-axis transitioning slowly
  // between values, it can jerk around.)
  var old_window = this.xAxisRange();
  var new_window = [minDate, maxDate];
  this.zoomed_x_ = true;
  var that = this;
  this.doAnimatedZoom(old_window, new_window, null, null, function() {
    if (that.getFunctionOption("zoomCallback")) {
      that.getFunctionOption("zoomCallback").call(that,
          minDate, maxDate, that.yAxisRanges());
    }
  });
};

/**
 * Zoom to something containing [lowY, highY]. These are pixel coordinates in
 * the canvas. This function redraws the graph.
 *
 * @param {number} lowY The topmost pixel value that should be visible.
 * @param {number} highY The lowest pixel value that should be visible.
 * @private
 */
Dygraph.prototype.doZoomY_ = function(lowY, highY) {
  this.currentZoomRectArgs_ = null;
  // Find the highest and lowest values in pixel range for each axis.
  // Note that lowY (in pixels) corresponds to the max Value (in data coords).
  // This is because pixels increase as you go down on the screen, whereas data
  // coordinates increase as you go up the screen.
  var oldValueRanges = this.yAxisRanges();
  var newValueRanges = [];
  for (var i = 0; i < this.axes_.length; i++) {
    var hi = this.toDataYCoord(lowY, i);
    var low = this.toDataYCoord(highY, i);
    newValueRanges.push([low, hi]);
  }

  this.zoomed_y_ = true;
  var that = this;
  this.doAnimatedZoom(null, null, oldValueRanges, newValueRanges, function() {
    if (that.getFunctionOption("zoomCallback")) {
      var xRange = that.xAxisRange();
      that.getFunctionOption("zoomCallback").call(that,
          xRange[0], xRange[1], that.yAxisRanges());
    }
  });
};

/**
 * Transition function to use in animations. Returns values between 0.0
 * (totally old values) and 1.0 (totally new values) for each frame.
 * @private
 */
Dygraph.zoomAnimationFunction = function(frame, numFrames) {
  var k = 1.5;
  return (1.0 - Math.pow(k, -frame)) / (1.0 - Math.pow(k, -numFrames));
};

/**
 * Reset the zoom to the original view coordinates. This is the same as
 * double-clicking on the graph.
 */
Dygraph.prototype.resetZoom = function() {
  var dirty = false, dirtyX = false, dirtyY = false;
  if (this.dateWindow_ !== null) {
    dirty = true;
    dirtyX = true;
  }

  for (var i = 0; i < this.axes_.length; i++) {
    if (typeof(this.axes_[i].valueWindow) !== 'undefined' && this.axes_[i].valueWindow !== null) {
      dirty = true;
      dirtyY = true;
    }
  }

  // Clear any selection, since it's likely to be drawn in the wrong place.
  this.clearSelection();

  if (dirty) {
    this.zoomed_x_ = false;
    this.zoomed_y_ = false;

    var minDate = this.rawData_[0][0];
    var maxDate = this.rawData_[this.rawData_.length - 1][0];

    // With only one frame, don't bother calculating extreme ranges.
    // TODO(danvk): merge this block w/ the code below.
    if (!this.getBooleanOption("animatedZooms")) {
      this.dateWindow_ = null;
      for (i = 0; i < this.axes_.length; i++) {
        if (this.axes_[i].valueWindow !== null) {
          delete this.axes_[i].valueWindow;
        }
      }
      this.drawGraph_();
      if (this.getFunctionOption("zoomCallback")) {
        this.getFunctionOption("zoomCallback").call(this,
            minDate, maxDate, this.yAxisRanges());
      }
      return;
    }

    var oldWindow=null, newWindow=null, oldValueRanges=null, newValueRanges=null;
    if (dirtyX) {
      oldWindow = this.xAxisRange();
      newWindow = [minDate, maxDate];
    }

    if (dirtyY) {
      oldValueRanges = this.yAxisRanges();
      // TODO(danvk): this is pretty inefficient
      var packed = this.gatherDatasets_(this.rolledSeries_, null);
      var extremes = packed.extremes;

      // this has the side-effect of modifying this.axes_.
      // this doesn't make much sense in this context, but it's convenient (we
      // need this.axes_[*].extremeValues) and not harmful since we'll be
      // calling drawGraph_ shortly, which clobbers these values.
      this.computeYAxisRanges_(extremes);

      newValueRanges = [];
      for (i = 0; i < this.axes_.length; i++) {
        var axis = this.axes_[i];
        newValueRanges.push((axis.valueRange !== null &&
                             axis.valueRange !== undefined) ?
                            axis.valueRange : axis.extremeRange);
      }
    }

    var that = this;
    this.doAnimatedZoom(oldWindow, newWindow, oldValueRanges, newValueRanges,
        function() {
          that.dateWindow_ = null;
          for (var i = 0; i < that.axes_.length; i++) {
            if (that.axes_[i].valueWindow !== null) {
              delete that.axes_[i].valueWindow;
            }
          }
          if (that.getFunctionOption("zoomCallback")) {
            that.getFunctionOption("zoomCallback").call(that,
                minDate, maxDate, that.yAxisRanges());
          }
        });
  }
};

/**
 * Combined animation logic for all zoom functions.
 * either the x parameters or y parameters may be null.
 * @private
 */
Dygraph.prototype.doAnimatedZoom = function(oldXRange, newXRange, oldYRanges, newYRanges, callback) {
  var steps = this.getBooleanOption("animatedZooms") ?
      Dygraph.ANIMATION_STEPS : 1;

  var windows = [];
  var valueRanges = [];
  var step, frac;

  if (oldXRange !== null && newXRange !== null) {
    for (step = 1; step <= steps; step++) {
      frac = Dygraph.zoomAnimationFunction(step, steps);
      windows[step-1] = [oldXRange[0]*(1-frac) + frac*newXRange[0],
                         oldXRange[1]*(1-frac) + frac*newXRange[1]];
    }
  }

  if (oldYRanges !== null && newYRanges !== null) {
    for (step = 1; step <= steps; step++) {
      frac = Dygraph.zoomAnimationFunction(step, steps);
      var thisRange = [];
      for (var j = 0; j < this.axes_.length; j++) {
        thisRange.push([oldYRanges[j][0]*(1-frac) + frac*newYRanges[j][0],
                        oldYRanges[j][1]*(1-frac) + frac*newYRanges[j][1]]);
      }
      valueRanges[step-1] = thisRange;
    }
  }

  var that = this;
  Dygraph.repeatAndCleanup(function(step) {
    if (valueRanges.length) {
      for (var i = 0; i < that.axes_.length; i++) {
        var w = valueRanges[step][i];
        that.axes_[i].valueWindow = [w[0], w[1]];
      }
    }
    if (windows.length) {
      that.dateWindow_ = windows[step];
    }
    that.drawGraph_();
  }, steps, Dygraph.ANIMATION_DURATION / steps, callback);
};

/**
 * Get the current graph's area object.
 *
 * Returns: {x, y, w, h}
 */
Dygraph.prototype.getArea = function() {
  return this.plotter_.area;
};

/**
 * Convert a mouse event to DOM coordinates relative to the graph origin.
 *
 * Returns a two-element array: [X, Y].
 */
Dygraph.prototype.eventToDomCoords = function(event) {
  if (event.offsetX && event.offsetY) {
    return [ event.offsetX, event.offsetY ];
  } else {
    var eventElementPos = Dygraph.findPos(this.mouseEventElement_);
    var canvasx = Dygraph.pageX(event) - eventElementPos.x;
    var canvasy = Dygraph.pageY(event) - eventElementPos.y;
    return [canvasx, canvasy];
  }
};

/**
 * Given a canvas X coordinate, find the closest row.
 * @param {number} domX graph-relative DOM X coordinate
 * Returns {number} row number.
 * @private
 */
Dygraph.prototype.findClosestRow = function(domX) {
  var minDistX = Infinity;
  var closestRow = -1;
  var sets = this.layout_.points;
  for (var i = 0; i < sets.length; i++) {
    var points = sets[i];
    var len = points.length;
    for (var j = 0; j < len; j++) {
      var point = points[j];
      if (!Dygraph.isValidPoint(point, true)) continue;
      var dist = Math.abs(point.canvasx - domX);
      if (dist < minDistX) {
        minDistX = dist;
        closestRow = point.idx;
      }
    }
  }

  return closestRow;
};

/**
 * Given canvas X,Y coordinates, find the closest point.
 *
 * This finds the individual data point across all visible series
 * that's closest to the supplied DOM coordinates using the standard
 * Euclidean X,Y distance.
 *
 * @param {number} domX graph-relative DOM X coordinate
 * @param {number} domY graph-relative DOM Y coordinate
 * Returns: {row, seriesName, point}
 * @private
 */
Dygraph.prototype.findClosestPoint = function(domX, domY) {
  var minDist = Infinity;
  var dist, dx, dy, point, closestPoint, closestSeries, closestRow;
  for ( var setIdx = this.layout_.points.length - 1 ; setIdx >= 0 ; --setIdx ) {
    var points = this.layout_.points[setIdx];
    for (var i = 0; i < points.length; ++i) {
      point = points[i];
      if (!Dygraph.isValidPoint(point)) continue;
      dx = point.canvasx - domX;
      dy = point.canvasy - domY;
      dist = dx * dx + dy * dy;
      if (dist < minDist) {
        minDist = dist;
        closestPoint = point;
        closestSeries = setIdx;
        closestRow = point.idx;
      }
    }
  }
  var name = this.layout_.setNames[closestSeries];
  return {
    row: closestRow,
    seriesName: name,
    point: closestPoint
  };
};

/**
 * Given canvas X,Y coordinates, find the touched area in a stacked graph.
 *
 * This first finds the X data point closest to the supplied DOM X coordinate,
 * then finds the series which puts the Y coordinate on top of its filled area,
 * using linear interpolation between adjacent point pairs.
 *
 * @param {number} domX graph-relative DOM X coordinate
 * @param {number} domY graph-relative DOM Y coordinate
 * Returns: {row, seriesName, point}
 * @private
 */
Dygraph.prototype.findStackedPoint = function(domX, domY) {
  var row = this.findClosestRow(domX);
  var closestPoint, closestSeries;
  for (var setIdx = 0; setIdx < this.layout_.points.length; ++setIdx) {
    var boundary = this.getLeftBoundary_(setIdx);
    var rowIdx = row - boundary;
    var points = this.layout_.points[setIdx];
    if (rowIdx >= points.length) continue;
    var p1 = points[rowIdx];
    if (!Dygraph.isValidPoint(p1)) continue;
    var py = p1.canvasy;
    if (domX > p1.canvasx && rowIdx + 1 < points.length) {
      // interpolate series Y value using next point
      var p2 = points[rowIdx + 1];
      if (Dygraph.isValidPoint(p2)) {
        var dx = p2.canvasx - p1.canvasx;
        if (dx > 0) {
          var r = (domX - p1.canvasx) / dx;
          py += r * (p2.canvasy - p1.canvasy);
        }
      }
    } else if (domX < p1.canvasx && rowIdx > 0) {
      // interpolate series Y value using previous point
      var p0 = points[rowIdx - 1];
      if (Dygraph.isValidPoint(p0)) {
        var dx = p1.canvasx - p0.canvasx;
        if (dx > 0) {
          var r = (p1.canvasx - domX) / dx;
          py += r * (p0.canvasy - p1.canvasy);
        }
      }
    }
    // Stop if the point (domX, py) is above this series' upper edge
    if (setIdx === 0 || py < domY) {
      closestPoint = p1;
      closestSeries = setIdx;
    }
  }
  var name = this.layout_.setNames[closestSeries];
  return {
    row: row,
    seriesName: name,
    point: closestPoint
  };
};

/**
 * When the mouse moves in the canvas, display information about a nearby data
 * point and draw dots over those points in the data series. This function
 * takes care of cleanup of previously-drawn dots.
 * @param {Object} event The mousemove event from the browser.
 * @private
 */
Dygraph.prototype.mouseMove_ = function(event) {
  // This prevents JS errors when mousing over the canvas before data loads.
  var points = this.layout_.points;
  if (points === undefined || points === null) return;

  var canvasCoords = this.eventToDomCoords(event);
  var canvasx = canvasCoords[0];
  var canvasy = canvasCoords[1];

  var highlightSeriesOpts = this.getOption("highlightSeriesOpts");
  var selectionChanged = false;
  if (highlightSeriesOpts && !this.isSeriesLocked()) {
    var closest;
    if (this.getBooleanOption("stackedGraph")) {
      closest = this.findStackedPoint(canvasx, canvasy);
    } else {
      closest = this.findClosestPoint(canvasx, canvasy);
    }
    selectionChanged = this.setSelection(closest.row, closest.seriesName);
  } else {
    var idx = this.findClosestRow(canvasx);
    selectionChanged = this.setSelection(idx);
  }

  var callback = this.getFunctionOption("highlightCallback");
  if (callback && selectionChanged) {
    callback.call(this, event,
        this.lastx_,
        this.selPoints_,
        this.lastRow_,
        this.highlightSet_);
  }
};

/**
 * Fetch left offset from the specified set index or if not passed, the 
 * first defined boundaryIds record (see bug #236).
 * @private
 */
Dygraph.prototype.getLeftBoundary_ = function(setIdx) {
  if (this.boundaryIds_[setIdx]) {
      return this.boundaryIds_[setIdx][0];
  } else {
    for (var i = 0; i < this.boundaryIds_.length; i++) {
      if (this.boundaryIds_[i] !== undefined) {
        return this.boundaryIds_[i][0];
      }
    }
    return 0;
  }
};

Dygraph.prototype.animateSelection_ = function(direction) {
  var totalSteps = 10;
  var millis = 30;
  if (this.fadeLevel === undefined) this.fadeLevel = 0;
  if (this.animateId === undefined) this.animateId = 0;
  var start = this.fadeLevel;
  var steps = direction < 0 ? start : totalSteps - start;
  if (steps <= 0) {
    if (this.fadeLevel) {
      this.updateSelection_(1.0);
    }
    return;
  }

  var thisId = ++this.animateId;
  var that = this;
  Dygraph.repeatAndCleanup(
    function(n) {
      // ignore simultaneous animations
      if (that.animateId != thisId) return;

      that.fadeLevel += direction;
      if (that.fadeLevel === 0) {
        that.clearSelection();
      } else {
        that.updateSelection_(that.fadeLevel / totalSteps);
      }
    },
    steps, millis, function() {});
};

/**
 * Draw dots over the selectied points in the data series. This function
 * takes care of cleanup of previously-drawn dots.
 * @private
 */
Dygraph.prototype.updateSelection_ = function(opt_animFraction) {
  /*var defaultPrevented = */
  this.cascadeEvents_('select', {
    selectedRow: this.lastRow_,
    selectedX: this.lastx_,
    selectedPoints: this.selPoints_
  });
  // TODO(danvk): use defaultPrevented here?

  // Clear the previously drawn vertical, if there is one
  var i;
  var ctx = this.canvas_ctx_;
  if (this.getOption('highlightSeriesOpts')) {
    ctx.clearRect(0, 0, this.width_, this.height_);
    var alpha = 1.0 - this.getNumericOption('highlightSeriesBackgroundAlpha');
    if (alpha) {
      // Activating background fade includes an animation effect for a gradual
      // fade. TODO(klausw): make this independently configurable if it causes
      // issues? Use a shared preference to control animations?
      var animateBackgroundFade = true;
      if (animateBackgroundFade) {
        if (opt_animFraction === undefined) {
          // start a new animation
          this.animateSelection_(1);
          return;
        }
        alpha *= opt_animFraction;
      }
      ctx.fillStyle = 'rgba(255,255,255,' + alpha + ')';
      ctx.fillRect(0, 0, this.width_, this.height_);
    }

    // Redraw only the highlighted series in the interactive canvas (not the
    // static plot canvas, which is where series are usually drawn).
    this.plotter_._renderLineChart(this.highlightSet_, ctx);
  } else if (this.previousVerticalX_ >= 0) {
    // Determine the maximum highlight circle size.
    var maxCircleSize = 0;
    var labels = this.attr_('labels');
    for (i = 1; i < labels.length; i++) {
      var r = this.getNumericOption('highlightCircleSize', labels[i]);
      if (r > maxCircleSize) maxCircleSize = r;
    }
    var px = this.previousVerticalX_;
    ctx.clearRect(px - maxCircleSize - 1, 0,
                  2 * maxCircleSize + 2, this.height_);
  }

  if (this.isUsingExcanvas_ && this.currentZoomRectArgs_) {
    Dygraph.prototype.drawZoomRect_.apply(this, this.currentZoomRectArgs_);
  }

  if (this.selPoints_.length > 0) {
    // Draw colored circles over the center of each selected point
    var canvasx = this.selPoints_[0].canvasx;
    ctx.save();
    for (i = 0; i < this.selPoints_.length; i++) {
      var pt = this.selPoints_[i];
      if (!Dygraph.isOK(pt.canvasy)) continue;

      var circleSize = this.getNumericOption('highlightCircleSize', pt.name);
      var callback = this.getFunctionOption("drawHighlightPointCallback", pt.name);
      var color = this.plotter_.colors[pt.name];
      if (!callback) {
        callback = Dygraph.Circles.DEFAULT;
      }
      ctx.lineWidth = this.getNumericOption('strokeWidth', pt.name);
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      callback.call(this, this, pt.name, ctx, canvasx, pt.canvasy,
          color, circleSize, pt.idx);
    }
    ctx.restore();

    this.previousVerticalX_ = canvasx;
  }
};

/**
 * Manually set the selected points and display information about them in the
 * legend. The selection can be cleared using clearSelection() and queried
 * using getSelection().
 * @param {number} row Row number that should be highlighted (i.e. appear with
 * hover dots on the chart).
 * @param {seriesName} optional series name to highlight that series with the
 * the highlightSeriesOpts setting.
 * @param { locked } optional If true, keep seriesName selected when mousing
 * over the graph, disabling closest-series highlighting. Call clearSelection()
 * to unlock it.
 */
Dygraph.prototype.setSelection = function(row, opt_seriesName, opt_locked) {
  // Extract the points we've selected
  this.selPoints_ = [];

  var changed = false;
  if (row !== false && row >= 0) {
    if (row != this.lastRow_) changed = true;
    this.lastRow_ = row;
    for (var setIdx = 0; setIdx < this.layout_.points.length; ++setIdx) {
      var points = this.layout_.points[setIdx];
      // Check if the point at the appropriate index is the point we're looking
      // for.  If it is, just use it, otherwise search the array for a point
      // in the proper place.
      var setRow = row - this.getLeftBoundary_(setIdx);
      if (setRow < points.length && points[setRow].idx == row) {
        var point = points[setRow];
        if (point.yval !== null) this.selPoints_.push(point);
      } else {
        for (var pointIdx = 0; pointIdx < points.length; ++pointIdx) {
          var point = points[pointIdx];
          if (point.idx == row) {
            if (point.yval !== null) {
              this.selPoints_.push(point);
            }
            break;
          }
        }
      }
    }
  } else {
    if (this.lastRow_ >= 0) changed = true;
    this.lastRow_ = -1;
  }

  if (this.selPoints_.length) {
    this.lastx_ = this.selPoints_[0].xval;
  } else {
    this.lastx_ = -1;
  }

  if (opt_seriesName !== undefined) {
    if (this.highlightSet_ !== opt_seriesName) changed = true;
    this.highlightSet_ = opt_seriesName;
  }

  if (opt_locked !== undefined) {
    this.lockedSet_ = opt_locked;
  }

  if (changed) {
    this.updateSelection_(undefined);
  }
  return changed;
};

/**
 * The mouse has left the canvas. Clear out whatever artifacts remain
 * @param {Object} event the mouseout event from the browser.
 * @private
 */
Dygraph.prototype.mouseOut_ = function(event) {
  if (this.getFunctionOption("unhighlightCallback")) {
    this.getFunctionOption("unhighlightCallback").call(this, event);
  }

  if (this.getBooleanOption("hideOverlayOnMouseOut") && !this.lockedSet_) {
    this.clearSelection();
  }
};

/**
 * Clears the current selection (i.e. points that were highlighted by moving
 * the mouse over the chart).
 */
Dygraph.prototype.clearSelection = function() {
  this.cascadeEvents_('deselect', {});

  this.lockedSet_ = false;
  // Get rid of the overlay data
  if (this.fadeLevel) {
    this.animateSelection_(-1);
    return;
  }
  this.canvas_ctx_.clearRect(0, 0, this.width_, this.height_);
  this.fadeLevel = 0;
  this.selPoints_ = [];
  this.lastx_ = -1;
  this.lastRow_ = -1;
  this.highlightSet_ = null;
};

/**
 * Returns the number of the currently selected row. To get data for this row,
 * you can use the getValue method.
 * @return {number} row number, or -1 if nothing is selected
 */
Dygraph.prototype.getSelection = function() {
  if (!this.selPoints_ || this.selPoints_.length < 1) {
    return -1;
  }

  for (var setIdx = 0; setIdx < this.layout_.points.length; setIdx++) {
    var points = this.layout_.points[setIdx];
    for (var row = 0; row < points.length; row++) {
      if (points[row].x == this.selPoints_[0].x) {
        return points[row].idx;
      }
    }
  }
  return -1;
};

/**
 * Returns the name of the currently-highlighted series.
 * Only available when the highlightSeriesOpts option is in use.
 */
Dygraph.prototype.getHighlightSeries = function() {
  return this.highlightSet_;
};

/**
 * Returns true if the currently-highlighted series was locked
 * via setSelection(..., seriesName, true).
 */
Dygraph.prototype.isSeriesLocked = function() {
  return this.lockedSet_;
};

/**
 * Fires when there's data available to be graphed.
 * @param {string} data Raw CSV data to be plotted
 * @private
 */
Dygraph.prototype.loadedEvent_ = function(data) {
  this.rawData_ = this.parseCSV_(data);
  this.cascadeDataDidUpdateEvent_();
  this.predraw_();
};

/**
 * Add ticks on the x-axis representing years, months, quarters, weeks, or days
 * @private
 */
Dygraph.prototype.addXTicks_ = function() {
  // Determine the correct ticks scale on the x-axis: quarterly, monthly, ...
  var range;
  if (this.dateWindow_) {
    range = [this.dateWindow_[0], this.dateWindow_[1]];
  } else {
    range = this.xAxisExtremes();
  }

  var xAxisOptionsView = this.optionsViewForAxis_('x');
  var xTicks = xAxisOptionsView('ticker')(
      range[0],
      range[1],
      this.plotter_.area.w,  // TODO(danvk): should be area.width
      xAxisOptionsView,
      this);
  // var msg = 'ticker(' + range[0] + ', ' + range[1] + ', ' + this.width_ + ', ' + this.attr_('pixelsPerXLabel') + ') -> ' + JSON.stringify(xTicks);
  // console.log(msg);
  this.layout_.setXTicks(xTicks);
};

/**
 * Returns the correct handler class for the currently set options.
 * @private
 */
Dygraph.prototype.getHandlerClass_ = function() {
  var handlerClass;
  if (this.attr_('dataHandler')) {
    handlerClass =  this.attr_('dataHandler');
  } else if (this.fractions_) {
    if (this.getBooleanOption('errorBars')) {
      handlerClass = Dygraph.DataHandlers.FractionsBarsHandler;
    } else {
      handlerClass = Dygraph.DataHandlers.DefaultFractionHandler;
    }
  } else if (this.getBooleanOption('customBars')) {
    handlerClass = Dygraph.DataHandlers.CustomBarsHandler;
  } else if (this.getBooleanOption('errorBars')) {
    handlerClass = Dygraph.DataHandlers.ErrorBarsHandler;
  } else {
    handlerClass = Dygraph.DataHandlers.DefaultHandler;
  }
  return handlerClass;
};

/**
 * @private
 * This function is called once when the chart's data is changed or the options
 * dictionary is updated. It is _not_ called when the user pans or zooms. The
 * idea is that values derived from the chart's data can be computed here,
 * rather than every time the chart is drawn. This includes things like the
 * number of axes, rolling averages, etc.
 */
Dygraph.prototype.predraw_ = function() {
  var start = new Date();
  
  // Create the correct dataHandler
  this.dataHandler_ = new (this.getHandlerClass_())();

  this.layout_.computePlotArea();

  // TODO(danvk): move more computations out of drawGraph_ and into here.
  this.computeYAxes_();

  if (!this.is_initial_draw_) {
    this.canvas_ctx_.restore();
    this.hidden_ctx_.restore();
  }

  this.canvas_ctx_.save();
  this.hidden_ctx_.save();

  // Create a new plotter.
  this.plotter_ = new DygraphCanvasRenderer(this,
                                            this.hidden_,
                                            this.hidden_ctx_,
                                            this.layout_);

  // The roller sits in the bottom left corner of the chart. We don't know where
  // this will be until the options are available, so it's positioned here.
  this.createRollInterface_();

  this.cascadeEvents_('predraw');

  // Convert the raw data (a 2D array) into the internal format and compute
  // rolling averages.
  this.rolledSeries_ = [null];  // x-axis is the first series and it's special
  for (var i = 1; i < this.numColumns(); i++) {
    // var logScale = this.attr_('logscale', i); // TODO(klausw): this looks wrong // konigsberg thinks so too.
    var series = this.dataHandler_.extractSeries(this.rawData_, i, this.attributes_);
    if (this.rollPeriod_ > 1) {
      series = this.dataHandler_.rollingAverage(series, this.rollPeriod_, this.attributes_);
    }
    
    this.rolledSeries_.push(series);
  }

  // If the data or options have changed, then we'd better redraw.
  this.drawGraph_();

  // This is used to determine whether to do various animations.
  var end = new Date();
  this.drawingTimeMs_ = (end - start);
};

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
Dygraph.PointType = undefined;

/**
 * Calculates point stacking for stackedGraph=true.
 *
 * For stacking purposes, interpolate or extend neighboring data across
 * NaN values based on stackedGraphNaNFill settings. This is for display
 * only, the underlying data value as shown in the legend remains NaN.
 *
 * @param {Array.<Dygraph.PointType>} points Point array for a single series.
 *     Updates each Point's yval_stacked property.
 * @param {Array.<number>} cumulativeYval Accumulated top-of-graph stacked Y
 *     values for the series seen so far. Index is the row number. Updated
 *     based on the current series's values.
 * @param {Array.<number>} seriesExtremes Min and max values, updated
 *     to reflect the stacked values.
 * @param {string} fillMethod Interpolation method, one of 'all', 'inside', or
 *     'none'.
 * @private
 */
Dygraph.stackPoints_ = function(
    points, cumulativeYval, seriesExtremes, fillMethod) {
  var lastXval = null;
  var prevPoint = null;
  var nextPoint = null;
  var nextPointIdx = -1;

  // Find the next stackable point starting from the given index.
  var updateNextPoint = function(idx) {
    // If we've previously found a non-NaN point and haven't gone past it yet,
    // just use that.
    if (nextPointIdx >= idx) return;

    // We haven't found a non-NaN point yet or have moved past it,
    // look towards the right to find a non-NaN point.
    for (var j = idx; j < points.length; ++j) {
      // Clear out a previously-found point (if any) since it's no longer
      // valid, we shouldn't use it for interpolation anymore.
      nextPoint = null;
      if (!isNaN(points[j].yval) && points[j].yval !== null) {
        nextPointIdx = j;
        nextPoint = points[j];
        break;
      }
    }
  };

  for (var i = 0; i < points.length; ++i) {
    var point = points[i];
    var xval = point.xval;
    if (cumulativeYval[xval] === undefined) {
      cumulativeYval[xval] = 0;
    }

    var actualYval = point.yval;
    if (isNaN(actualYval) || actualYval === null) {
      if(fillMethod == 'none') {
        actualYval = 0;
      } else {
        // Interpolate/extend for stacking purposes if possible.
        updateNextPoint(i);
        if (prevPoint && nextPoint && fillMethod != 'none') {
          // Use linear interpolation between prevPoint and nextPoint.
          actualYval = prevPoint.yval + (nextPoint.yval - prevPoint.yval) *
              ((xval - prevPoint.xval) / (nextPoint.xval - prevPoint.xval));
        } else if (prevPoint && fillMethod == 'all') {
          actualYval = prevPoint.yval;
        } else if (nextPoint && fillMethod == 'all') {
          actualYval = nextPoint.yval;
        } else {
          actualYval = 0;
        }
      }
    } else {
      prevPoint = point;
    }

    var stackedYval = cumulativeYval[xval];
    if (lastXval != xval) {
      // If an x-value is repeated, we ignore the duplicates.
      stackedYval += actualYval;
      cumulativeYval[xval] = stackedYval;
    }
    lastXval = xval;

    point.yval_stacked = stackedYval;

    if (stackedYval > seriesExtremes[1]) {
      seriesExtremes[1] = stackedYval;
    }
    if (stackedYval < seriesExtremes[0]) {
      seriesExtremes[0] = stackedYval;
    }
  }
};


/**
 * Loop over all fields and create datasets, calculating extreme y-values for
 * each series and extreme x-indices as we go.
 *
 * dateWindow is passed in as an explicit parameter so that we can compute
 * extreme values "speculatively", i.e. without actually setting state on the
 * dygraph.
 *
 * @param {Array.<Array.<Array.<(number|Array<number>)>>} rolledSeries, where
 *     rolledSeries[seriesIndex][row] = raw point, where
 *     seriesIndex is the column number starting with 1, and
 *     rawPoint is [x,y] or [x, [y, err]] or [x, [y, yminus, yplus]].
 * @param {?Array.<number>} dateWindow [xmin, xmax] pair, or null.
 * @return {{
 *     points: Array.<Array.<Dygraph.PointType>>,
 *     seriesExtremes: Array.<Array.<number>>,
 *     boundaryIds: Array.<number>}}
 * @private
 */
Dygraph.prototype.gatherDatasets_ = function(rolledSeries, dateWindow) {
  var boundaryIds = [];
  var points = [];
  var cumulativeYval = [];  // For stacked series.
  var extremes = {};  // series name -> [low, high]
  var seriesIdx, sampleIdx;
  var firstIdx, lastIdx;
  var axisIdx;
  
  // Loop over the fields (series).  Go from the last to the first,
  // because if they're stacked that's how we accumulate the values.
  var num_series = rolledSeries.length - 1;
  var series;
  for (seriesIdx = num_series; seriesIdx >= 1; seriesIdx--) {
    if (!this.visibility()[seriesIdx - 1]) continue;

    // Prune down to the desired range, if necessary (for zooming)
    // Because there can be lines going to points outside of the visible area,
    // we actually prune to visible points, plus one on either side.
    if (dateWindow) {
      series = rolledSeries[seriesIdx];
      var low = dateWindow[0];
      var high = dateWindow[1];

      // TODO(danvk): do binary search instead of linear search.
      // TODO(danvk): pass firstIdx and lastIdx directly to the renderer.
      firstIdx = null; 
      lastIdx = null;
      for (sampleIdx = 0; sampleIdx < series.length; sampleIdx++) {
        if (series[sampleIdx][0] >= low && firstIdx === null) {
          firstIdx = sampleIdx;
        }
        if (series[sampleIdx][0] <= high) {
          lastIdx = sampleIdx;
        }
      }

      if (firstIdx === null) firstIdx = 0;
      var correctedFirstIdx = firstIdx;
      var isInvalidValue = true;
      while (isInvalidValue && correctedFirstIdx > 0) {
        correctedFirstIdx--;
        // check if the y value is null.
        isInvalidValue = series[correctedFirstIdx][1] === null;
      }

      if (lastIdx === null) lastIdx = series.length - 1;
      var correctedLastIdx = lastIdx;
      isInvalidValue = true;
      while (isInvalidValue && correctedLastIdx < series.length - 1) {
        correctedLastIdx++;
        isInvalidValue = series[correctedLastIdx][1] === null;
      }

      if (correctedFirstIdx!==firstIdx) {
        firstIdx = correctedFirstIdx;
      }
      if (correctedLastIdx !== lastIdx) {
        lastIdx = correctedLastIdx;
      }
      
      boundaryIds[seriesIdx-1] = [firstIdx, lastIdx];
      
      // .slice's end is exclusive, we want to include lastIdx.
      series = series.slice(firstIdx, lastIdx + 1);
    } else {
      series = rolledSeries[seriesIdx];
      boundaryIds[seriesIdx-1] = [0, series.length-1];
    }

    var seriesName = this.attr_("labels")[seriesIdx];
    var seriesExtremes = this.dataHandler_.getExtremeYValues(series, 
        dateWindow, this.getBooleanOption("stepPlot",seriesName));

    var seriesPoints = this.dataHandler_.seriesToPoints(series, 
        seriesName, boundaryIds[seriesIdx-1][0]);

    if (this.getBooleanOption("stackedGraph")) {
      axisIdx = this.attributes_.axisForSeries(seriesName);
      if (cumulativeYval[axisIdx] === undefined) {
        cumulativeYval[axisIdx] = [];
      }
      Dygraph.stackPoints_(seriesPoints, cumulativeYval[axisIdx], seriesExtremes,
                           this.getBooleanOption("stackedGraphNaNFill"));
    }

    extremes[seriesName] = seriesExtremes;
    points[seriesIdx] = seriesPoints;
  }

  return { points: points, extremes: extremes, boundaryIds: boundaryIds };
};

/**
 * Update the graph with new data. This method is called when the viewing area
 * has changed. If the underlying data or options have changed, predraw_ will
 * be called before drawGraph_ is called.
 *
 * @private
 */
Dygraph.prototype.drawGraph_ = function() {
  var start = new Date();

  // This is used to set the second parameter to drawCallback, below.
  var is_initial_draw = this.is_initial_draw_;
  this.is_initial_draw_ = false;

  this.layout_.removeAllDatasets();
  this.setColors_();
  this.attrs_.pointSize = 0.5 * this.getNumericOption('highlightCircleSize');

  var packed = this.gatherDatasets_(this.rolledSeries_, this.dateWindow_);
  var points = packed.points;
  var extremes = packed.extremes;
  this.boundaryIds_ = packed.boundaryIds;

  this.setIndexByName_ = {};
  var labels = this.attr_("labels");
  if (labels.length > 0) {
    this.setIndexByName_[labels[0]] = 0;
  }
  var dataIdx = 0;
  for (var i = 1; i < points.length; i++) {
    this.setIndexByName_[labels[i]] = i;
    if (!this.visibility()[i - 1]) continue;
    this.layout_.addDataset(labels[i], points[i]);
    this.datasetIndex_[i] = dataIdx++;
  }

  this.computeYAxisRanges_(extremes);
  this.layout_.setYAxes(this.axes_);

  this.addXTicks_();

  // Save the X axis zoomed status as the updateOptions call will tend to set it erroneously
  var tmp_zoomed_x = this.zoomed_x_;
  // Tell PlotKit to use this new data and render itself
  this.zoomed_x_ = tmp_zoomed_x;
  this.layout_.evaluate();
  this.renderGraph_(is_initial_draw);

  if (this.getStringOption("timingName")) {
    var end = new Date();
    console.log(this.getStringOption("timingName") + " - drawGraph: " + (end - start) + "ms");
  }
};

/**
 * This does the work of drawing the chart. It assumes that the layout and axis
 * scales have already been set (e.g. by predraw_).
 *
 * @private
 */
Dygraph.prototype.renderGraph_ = function(is_initial_draw) {
  this.cascadeEvents_('clearChart');
  this.plotter_.clear();

  if (this.getFunctionOption('underlayCallback')) {
    // NOTE: we pass the dygraph object to this callback twice to avoid breaking
    // users who expect a deprecated form of this callback.
    this.getFunctionOption('underlayCallback').call(this,
        this.hidden_ctx_, this.layout_.getPlotArea(), this, this);
  }

  var e = {
    canvas: this.hidden_,
    drawingContext: this.hidden_ctx_
  };
  this.cascadeEvents_('willDrawChart', e);
  this.plotter_.render();
  this.cascadeEvents_('didDrawChart', e);
  this.lastRow_ = -1;  // because plugins/legend.js clears the legend

  // TODO(danvk): is this a performance bottleneck when panning?
  // The interaction canvas should already be empty in that situation.
  this.canvas_.getContext('2d').clearRect(0, 0, this.width_, this.height_);

  if (this.getFunctionOption("drawCallback") !== null) {
    this.getFunctionOption("drawCallback").call(this, this, is_initial_draw);
  }
  if (is_initial_draw) {
    this.readyFired_ = true;
    while (this.readyFns_.length > 0) {
      var fn = this.readyFns_.pop();
      fn(this);
    }
  }
};

/**
 * @private
 * Determine properties of the y-axes which are independent of the data
 * currently being displayed. This includes things like the number of axes and
 * the style of the axes. It does not include the range of each axis and its
 * tick marks.
 * This fills in this.axes_.
 * axes_ = [ { options } ]
 *   indices are into the axes_ array.
 */
Dygraph.prototype.computeYAxes_ = function() {
  // Preserve valueWindow settings if they exist, and if the user hasn't
  // specified a new valueRange.
  var valueWindows, axis, index, opts, v;
  if (this.axes_ !== undefined && this.user_attrs_.hasOwnProperty("valueRange") === false) {
    valueWindows = [];
    for (index = 0; index < this.axes_.length; index++) {
      valueWindows.push(this.axes_[index].valueWindow);
    }
  }

  // this.axes_ doesn't match this.attributes_.axes_.options. It's used for
  // data computation as well as options storage.
  // Go through once and add all the axes.
  this.axes_ = [];

  for (axis = 0; axis < this.attributes_.numAxes(); axis++) {
    // Add a new axis, making a copy of its per-axis options.
    opts = { g : this };
    Dygraph.update(opts, this.attributes_.axisOptions(axis));
    this.axes_[axis] = opts;
  }


  // Copy global valueRange option over to the first axis.
  // NOTE(konigsberg): Are these two statements necessary?
  // I tried removing it. The automated tests pass, and manually
  // messing with tests/zoom.html showed no trouble.
  v = this.attr_('valueRange');
  if (v) this.axes_[0].valueRange = v;

  if (valueWindows !== undefined) {
    // Restore valueWindow settings.

    // When going from two axes back to one, we only restore
    // one axis.
    var idxCount = Math.min(valueWindows.length, this.axes_.length);

    for (index = 0; index < idxCount; index++) {
      this.axes_[index].valueWindow = valueWindows[index];
    }
  }

  for (axis = 0; axis < this.axes_.length; axis++) {
    if (axis === 0) {
      opts = this.optionsViewForAxis_('y' + (axis ? '2' : ''));
      v = opts("valueRange");
      if (v) this.axes_[axis].valueRange = v;
    } else {  // To keep old behavior
      var axes = this.user_attrs_.axes;
      if (axes && axes.y2) {
        v = axes.y2.valueRange;
        if (v) this.axes_[axis].valueRange = v;
      }
    }
  }
};

/**
 * Returns the number of y-axes on the chart.
 * @return {number} the number of axes.
 */
Dygraph.prototype.numAxes = function() {
  return this.attributes_.numAxes();
};

/**
 * @private
 * Returns axis properties for the given series.
 * @param {string} setName The name of the series for which to get axis
 * properties, e.g. 'Y1'.
 * @return {Object} The axis properties.
 */
Dygraph.prototype.axisPropertiesForSeries = function(series) {
  // TODO(danvk): handle errors.
  return this.axes_[this.attributes_.axisForSeries(series)];
};

/**
 * @private
 * Determine the value range and tick marks for each axis.
 * @param {Object} extremes A mapping from seriesName -> [low, high]
 * This fills in the valueRange and ticks fields in each entry of this.axes_.
 */
Dygraph.prototype.computeYAxisRanges_ = function(extremes) {
  var isNullUndefinedOrNaN = function(num) {
    return isNaN(parseFloat(num));
  };
  var numAxes = this.attributes_.numAxes();
  var ypadCompat, span, series, ypad;
  
  var p_axis;

  // Compute extreme values, a span and tick marks for each axis.
  for (var i = 0; i < numAxes; i++) {
    var axis = this.axes_[i];
    var logscale = this.attributes_.getForAxis("logscale", i);
    var includeZero = this.attributes_.getForAxis("includeZero", i);
    var independentTicks = this.attributes_.getForAxis("independentTicks", i);
    series = this.attributes_.seriesForAxis(i);

    // Add some padding. This supports two Y padding operation modes:
    //
    // - backwards compatible (yRangePad not set):
    //   10% padding for automatic Y ranges, but not for user-supplied
    //   ranges, and move a close-to-zero edge to zero except if
    //   avoidMinZero is set, since drawing at the edge results in
    //   invisible lines. Unfortunately lines drawn at the edge of a
    //   user-supplied range will still be invisible. If logscale is
    //   set, add a variable amount of padding at the top but
    //   none at the bottom.
    //
    // - new-style (yRangePad set by the user):
    //   always add the specified Y padding.
    //
    ypadCompat = true;
    ypad = 0.1; // add 10%
    if (this.getNumericOption('yRangePad') !== null) {
      ypadCompat = false;
      // Convert pixel padding to ratio
      ypad = this.getNumericOption('yRangePad') / this.plotter_.area.h;
    }

    if (series.length === 0) {
      // If no series are defined or visible then use a reasonable default
      axis.extremeRange = [0, 1];
    } else {
      // Calculate the extremes of extremes.
      var minY = Infinity;  // extremes[series[0]][0];
      var maxY = -Infinity;  // extremes[series[0]][1];
      var extremeMinY, extremeMaxY;

      for (var j = 0; j < series.length; j++) {
        // this skips invisible series
        if (!extremes.hasOwnProperty(series[j])) continue;

        // Only use valid extremes to stop null data series' from corrupting the scale.
        extremeMinY = extremes[series[j]][0];
        if (extremeMinY !== null) {
          minY = Math.min(extremeMinY, minY);
        }
        extremeMaxY = extremes[series[j]][1];
        if (extremeMaxY !== null) {
          maxY = Math.max(extremeMaxY, maxY);
        }
      }

      // Include zero if requested by the user.
      if (includeZero && !logscale) {
        if (minY > 0) minY = 0;
        if (maxY < 0) maxY = 0;
      }

      // Ensure we have a valid scale, otherwise default to [0, 1] for safety.
      if (minY == Infinity) minY = 0;
      if (maxY == -Infinity) maxY = 1;

      span = maxY - minY;
      // special case: if we have no sense of scale, center on the sole value.
      if (span === 0) {
        if (maxY !== 0) {
          span = Math.abs(maxY);
        } else {
          // ... and if the sole value is zero, use range 0-1.
          maxY = 1;
          span = 1;
        }
      }

      var maxAxisY, minAxisY;
      if (logscale) {
        if (ypadCompat) {
          maxAxisY = maxY + ypad * span;
          minAxisY = minY;
        } else {
          var logpad = Math.exp(Math.log(span) * ypad);
          maxAxisY = maxY * logpad;
          minAxisY = minY / logpad;
        }
      } else {
        maxAxisY = maxY + ypad * span;
        minAxisY = minY - ypad * span;

        // Backwards-compatible behavior: Move the span to start or end at zero if it's
        // close to zero, but not if avoidMinZero is set.
        if (ypadCompat && !this.getBooleanOption("avoidMinZero")) {
          if (minAxisY < 0 && minY >= 0) minAxisY = 0;
          if (maxAxisY > 0 && maxY <= 0) maxAxisY = 0;
        }
      }
      axis.extremeRange = [minAxisY, maxAxisY];
    }
    if (axis.valueWindow) {
      // This is only set if the user has zoomed on the y-axis. It is never set
      // by a user. It takes precedence over axis.valueRange because, if you set
      // valueRange, you'd still expect to be able to pan.
      axis.computedValueRange = [axis.valueWindow[0], axis.valueWindow[1]];
    } else if (axis.valueRange) {
      // This is a user-set value range for this axis.
      var y0 = isNullUndefinedOrNaN(axis.valueRange[0]) ? axis.extremeRange[0] : axis.valueRange[0];
      var y1 = isNullUndefinedOrNaN(axis.valueRange[1]) ? axis.extremeRange[1] : axis.valueRange[1];
      if (!ypadCompat) {
        if (axis.logscale) {
          var logpad = Math.exp(Math.log(span) * ypad);
          y0 *= logpad;
          y1 /= logpad;
        } else {
          span = y1 - y0;
          y0 -= span * ypad;
          y1 += span * ypad;
        }
      }
      axis.computedValueRange = [y0, y1];
    } else {
      axis.computedValueRange = axis.extremeRange;
    }
    
    
    if (independentTicks) {
      axis.independentTicks = independentTicks;
      var opts = this.optionsViewForAxis_('y' + (i ? '2' : ''));
      var ticker = opts('ticker');
      axis.ticks = ticker(axis.computedValueRange[0],
              axis.computedValueRange[1],
              this.plotter_.area.h,
              opts,
              this);
      // Define the first independent axis as primary axis.
      if (!p_axis) p_axis = axis;
    }
  }
  if (p_axis === undefined) {
    throw ("Configuration Error: At least one axis has to have the \"independentTicks\" option activated.");
  }
  // Add ticks. By default, all axes inherit the tick positions of the
  // primary axis. However, if an axis is specifically marked as having
  // independent ticks, then that is permissible as well.
  for (var i = 0; i < numAxes; i++) {
    var axis = this.axes_[i];
    
    if (!axis.independentTicks) {
      var opts = this.optionsViewForAxis_('y' + (i ? '2' : ''));
      var ticker = opts('ticker');
      var p_ticks = p_axis.ticks;
      var p_scale = p_axis.computedValueRange[1] - p_axis.computedValueRange[0];
      var scale = axis.computedValueRange[1] - axis.computedValueRange[0];
      var tick_values = [];
      for (var k = 0; k < p_ticks.length; k++) {
        var y_frac = (p_ticks[k].v - p_axis.computedValueRange[0]) / p_scale;
        var y_val = axis.computedValueRange[0] + y_frac * scale;
        tick_values.push(y_val);
      }

      axis.ticks = ticker(axis.computedValueRange[0],
                          axis.computedValueRange[1],
                          this.plotter_.area.h,
                          opts,
                          this,
                          tick_values);
    }
  }
};

/**
 * Detects the type of the str (date or numeric) and sets the various
 * formatting attributes in this.attrs_ based on this type.
 * @param {string} str An x value.
 * @private
 */
Dygraph.prototype.detectTypeFromString_ = function(str) {
  var isDate = false;
  var dashPos = str.indexOf('-');  // could be 2006-01-01 _or_ 1.0e-2
  if ((dashPos > 0 && (str[dashPos-1] != 'e' && str[dashPos-1] != 'E')) ||
      str.indexOf('/') >= 0 ||
      isNaN(parseFloat(str))) {
    isDate = true;
  } else if (str.length == 8 && str > '19700101' && str < '20371231') {
    // TODO(danvk): remove support for this format.
    isDate = true;
  }

  this.setXAxisOptions_(isDate);
};

Dygraph.prototype.setXAxisOptions_ = function(isDate) {
  if (isDate) {
    this.attrs_.xValueParser = Dygraph.dateParser;
    this.attrs_.axes.x.valueFormatter = Dygraph.dateValueFormatter;
    this.attrs_.axes.x.ticker = Dygraph.dateTicker;
    this.attrs_.axes.x.axisLabelFormatter = Dygraph.dateAxisLabelFormatter;
  } else {
    /** @private (shut up, jsdoc!) */
    this.attrs_.xValueParser = function(x) { return parseFloat(x); };
    // TODO(danvk): use Dygraph.numberValueFormatter here?
    /** @private (shut up, jsdoc!) */
    this.attrs_.axes.x.valueFormatter = function(x) { return x; };
    this.attrs_.axes.x.ticker = Dygraph.numericTicks;
    this.attrs_.axes.x.axisLabelFormatter = this.attrs_.axes.x.valueFormatter;
  }
};

/**
 * @private
 * Parses a string in a special csv format.  We expect a csv file where each
 * line is a date point, and the first field in each line is the date string.
 * We also expect that all remaining fields represent series.
 * if the errorBars attribute is set, then interpret the fields as:
 * date, series1, stddev1, series2, stddev2, ...
 * @param {[Object]} data See above.
 *
 * @return [Object] An array with one entry for each row. These entries
 * are an array of cells in that row. The first entry is the parsed x-value for
 * the row. The second, third, etc. are the y-values. These can take on one of
 * three forms, depending on the CSV and constructor parameters:
 * 1. numeric value
 * 2. [ value, stddev ]
 * 3. [ low value, center value, high value ]
 */
Dygraph.prototype.parseCSV_ = function(data) {
  var ret = [];
  var line_delimiter = Dygraph.detectLineDelimiter(data);
  var lines = data.split(line_delimiter || "\n");
  var vals, j;

  // Use the default delimiter or fall back to a tab if that makes sense.
  var delim = this.getStringOption('delimiter');
  if (lines[0].indexOf(delim) == -1 && lines[0].indexOf('\t') >= 0) {
    delim = '\t';
  }

  var start = 0;
  if (!('labels' in this.user_attrs_)) {
    // User hasn't explicitly set labels, so they're (presumably) in the CSV.
    start = 1;
    this.attrs_.labels = lines[0].split(delim);  // NOTE: _not_ user_attrs_.
    this.attributes_.reparseSeries();
  }
  var line_no = 0;

  var xParser;
  var defaultParserSet = false;  // attempt to auto-detect x value type
  var expectedCols = this.attr_("labels").length;
  var outOfOrder = false;
  for (var i = start; i < lines.length; i++) {
    var line = lines[i];
    line_no = i;
    if (line.length === 0) continue;  // skip blank lines
    if (line[0] == '#') continue;    // skip comment lines
    var inFields = line.split(delim);
    if (inFields.length < 2) continue;

    var fields = [];
    if (!defaultParserSet) {
      this.detectTypeFromString_(inFields[0]);
      xParser = this.getFunctionOption("xValueParser");
      defaultParserSet = true;
    }
    fields[0] = xParser(inFields[0], this);

    // If fractions are expected, parse the numbers as "A/B"
    if (this.fractions_) {
      for (j = 1; j < inFields.length; j++) {
        // TODO(danvk): figure out an appropriate way to flag parse errors.
        vals = inFields[j].split("/");
        if (vals.length != 2) {
          console.error('Expected fractional "num/den" values in CSV data ' +
                        "but found a value '" + inFields[j] + "' on line " +
                        (1 + i) + " ('" + line + "') which is not of this form.");
          fields[j] = [0, 0];
        } else {
          fields[j] = [Dygraph.parseFloat_(vals[0], i, line),
                       Dygraph.parseFloat_(vals[1], i, line)];
        }
      }
    } else if (this.getBooleanOption("errorBars")) {
      // If there are error bars, values are (value, stddev) pairs
      if (inFields.length % 2 != 1) {
        console.error('Expected alternating (value, stdev.) pairs in CSV data ' +
                      'but line ' + (1 + i) + ' has an odd number of values (' +
                      (inFields.length - 1) + "): '" + line + "'");
      }
      for (j = 1; j < inFields.length; j += 2) {
        fields[(j + 1) / 2] = [Dygraph.parseFloat_(inFields[j], i, line),
                               Dygraph.parseFloat_(inFields[j + 1], i, line)];
      }
    } else if (this.getBooleanOption("customBars")) {
      // Bars are a low;center;high tuple
      for (j = 1; j < inFields.length; j++) {
        var val = inFields[j];
        if (/^ *$/.test(val)) {
          fields[j] = [null, null, null];
        } else {
          vals = val.split(";");
          if (vals.length == 3) {
            fields[j] = [ Dygraph.parseFloat_(vals[0], i, line),
                          Dygraph.parseFloat_(vals[1], i, line),
                          Dygraph.parseFloat_(vals[2], i, line) ];
          } else {
            console.warn('When using customBars, values must be either blank ' +
                         'or "low;center;high" tuples (got "' + val +
                         '" on line ' + (1+i));
          }
        }
      }
    } else {
      // Values are just numbers
      for (j = 1; j < inFields.length; j++) {
        fields[j] = Dygraph.parseFloat_(inFields[j], i, line);
      }
    }
    if (ret.length > 0 && fields[0] < ret[ret.length - 1][0]) {
      outOfOrder = true;
    }

    if (fields.length != expectedCols) {
      console.error("Number of columns in line " + i + " (" + fields.length +
                    ") does not agree with number of labels (" + expectedCols +
                    ") " + line);
    }

    // If the user specified the 'labels' option and none of the cells of the
    // first row parsed correctly, then they probably double-specified the
    // labels. We go with the values set in the option, discard this row and
    // log a warning to the JS console.
    if (i === 0 && this.attr_('labels')) {
      var all_null = true;
      for (j = 0; all_null && j < fields.length; j++) {
        if (fields[j]) all_null = false;
      }
      if (all_null) {
        console.warn("The dygraphs 'labels' option is set, but the first row " +
                     "of CSV data ('" + line + "') appears to also contain " +
                     "labels. Will drop the CSV labels and use the option " +
                     "labels.");
        continue;
      }
    }
    ret.push(fields);
  }

  if (outOfOrder) {
    console.warn("CSV is out of order; order it correctly to speed loading.");
    ret.sort(function(a,b) { return a[0] - b[0]; });
  }

  return ret;
};

/**
 * The user has provided their data as a pre-packaged JS array. If the x values
 * are numeric, this is the same as dygraphs' internal format. If the x values
 * are dates, we need to convert them from Date objects to ms since epoch.
 * @param {!Array} data
 * @return {Object} data with numeric x values.
 * @private
 */
Dygraph.prototype.parseArray_ = function(data) {
  // Peek at the first x value to see if it's numeric.
  if (data.length === 0) {
    console.error("Can't plot empty data set");
    return null;
  }
  if (data[0].length === 0) {
    console.error("Data set cannot contain an empty row");
    return null;
  }

  var i;
  if (this.attr_("labels") === null) {
    console.warn("Using default labels. Set labels explicitly via 'labels' " +
                 "in the options parameter");
    this.attrs_.labels = [ "X" ];
    for (i = 1; i < data[0].length; i++) {
      this.attrs_.labels.push("Y" + i); // Not user_attrs_.
    }
    this.attributes_.reparseSeries();
  } else {
    var num_labels = this.attr_("labels");
    if (num_labels.length != data[0].length) {
      console.error("Mismatch between number of labels (" + num_labels + ")" +
                    " and number of columns in array (" + data[0].length + ")");
      return null;
    }
  }

  if (Dygraph.isDateLike(data[0][0])) {
    // Some intelligent defaults for a date x-axis.
    this.attrs_.axes.x.valueFormatter = Dygraph.dateValueFormatter;
    this.attrs_.axes.x.ticker = Dygraph.dateTicker;
    this.attrs_.axes.x.axisLabelFormatter = Dygraph.dateAxisLabelFormatter;

    // Assume they're all dates.
    var parsedData = Dygraph.clone(data);
    for (i = 0; i < data.length; i++) {
      if (parsedData[i].length === 0) {
        console.error("Row " + (1 + i) + " of data is empty");
        return null;
      }
      if (parsedData[i][0] === null ||
          typeof(parsedData[i][0].getTime) != 'function' ||
          isNaN(parsedData[i][0].getTime())) {
        console.error("x value in row " + (1 + i) + " is not a Date");
        return null;
      }
      parsedData[i][0] = parsedData[i][0].getTime();
    }
    return parsedData;
  } else {
    // Some intelligent defaults for a numeric x-axis.
    /** @private (shut up, jsdoc!) */
    this.attrs_.axes.x.valueFormatter = function(x) { return x; };
    this.attrs_.axes.x.ticker = Dygraph.numericTicks;
    this.attrs_.axes.x.axisLabelFormatter = Dygraph.numberAxisLabelFormatter;
    return data;
  }
};

/**
 * Parses a DataTable object from gviz.
 * The data is expected to have a first column that is either a date or a
 * number. All subsequent columns must be numbers. If there is a clear mismatch
 * between this.xValueParser_ and the type of the first column, it will be
 * fixed. Fills out rawData_.
 * @param {!google.visualization.DataTable} data See above.
 * @private
 */
Dygraph.prototype.parseDataTable_ = function(data) {
  var shortTextForAnnotationNum = function(num) {
    // converts [0-9]+ [A-Z][a-z]*
    // example: 0=A, 1=B, 25=Z, 26=Aa, 27=Ab
    // and continues like.. Ba Bb .. Za .. Zz..Aaa...Zzz Aaaa Zzzz
    var shortText = String.fromCharCode(65 /* A */ + num % 26);
    num = Math.floor(num / 26);
    while ( num > 0 ) {
      shortText = String.fromCharCode(65 /* A */ + (num - 1) % 26 ) + shortText.toLowerCase();
      num = Math.floor((num - 1) / 26);
    }
    return shortText;
  };

  var cols = data.getNumberOfColumns();
  var rows = data.getNumberOfRows();

  var indepType = data.getColumnType(0);
  if (indepType == 'date' || indepType == 'datetime') {
    this.attrs_.xValueParser = Dygraph.dateParser;
    this.attrs_.axes.x.valueFormatter = Dygraph.dateValueFormatter;
    this.attrs_.axes.x.ticker = Dygraph.dateTicker;
    this.attrs_.axes.x.axisLabelFormatter = Dygraph.dateAxisLabelFormatter;
  } else if (indepType == 'number') {
    this.attrs_.xValueParser = function(x) { return parseFloat(x); };
    this.attrs_.axes.x.valueFormatter = function(x) { return x; };
    this.attrs_.axes.x.ticker = Dygraph.numericTicks;
    this.attrs_.axes.x.axisLabelFormatter = this.attrs_.axes.x.valueFormatter;
  } else {
    console.error("only 'date', 'datetime' and 'number' types are supported " +
                  "for column 1 of DataTable input (Got '" + indepType + "')");
    return null;
  }

  // Array of the column indices which contain data (and not annotations).
  var colIdx = [];
  var annotationCols = {};  // data index -> [annotation cols]
  var hasAnnotations = false;
  var i, j;
  for (i = 1; i < cols; i++) {
    var type = data.getColumnType(i);
    if (type == 'number') {
      colIdx.push(i);
    } else if (type == 'string' && this.getBooleanOption('displayAnnotations')) {
      // This is OK -- it's an annotation column.
      var dataIdx = colIdx[colIdx.length - 1];
      if (!annotationCols.hasOwnProperty(dataIdx)) {
        annotationCols[dataIdx] = [i];
      } else {
        annotationCols[dataIdx].push(i);
      }
      hasAnnotations = true;
    } else {
      console.error("Only 'number' is supported as a dependent type with Gviz." +
                    " 'string' is only supported if displayAnnotations is true");
    }
  }

  // Read column labels
  // TODO(danvk): add support back for errorBars
  var labels = [data.getColumnLabel(0)];
  for (i = 0; i < colIdx.length; i++) {
    labels.push(data.getColumnLabel(colIdx[i]));
    if (this.getBooleanOption("errorBars")) i += 1;
  }
  this.attrs_.labels = labels;
  cols = labels.length;

  var ret = [];
  var outOfOrder = false;
  var annotations = [];
  for (i = 0; i < rows; i++) {
    var row = [];
    if (typeof(data.getValue(i, 0)) === 'undefined' ||
        data.getValue(i, 0) === null) {
      console.warn("Ignoring row " + i +
                   " of DataTable because of undefined or null first column.");
      continue;
    }

    if (indepType == 'date' || indepType == 'datetime') {
      row.push(data.getValue(i, 0).getTime());
    } else {
      row.push(data.getValue(i, 0));
    }
    if (!this.getBooleanOption("errorBars")) {
      for (j = 0; j < colIdx.length; j++) {
        var col = colIdx[j];
        row.push(data.getValue(i, col));
        if (hasAnnotations &&
            annotationCols.hasOwnProperty(col) &&
            data.getValue(i, annotationCols[col][0]) !== null) {
          var ann = {};
          ann.series = data.getColumnLabel(col);
          ann.xval = row[0];
          ann.shortText = shortTextForAnnotationNum(annotations.length);
          ann.text = '';
          for (var k = 0; k < annotationCols[col].length; k++) {
            if (k) ann.text += "\n";
            ann.text += data.getValue(i, annotationCols[col][k]);
          }
          annotations.push(ann);
        }
      }

      // Strip out infinities, which give dygraphs problems later on.
      for (j = 0; j < row.length; j++) {
        if (!isFinite(row[j])) row[j] = null;
      }
    } else {
      for (j = 0; j < cols - 1; j++) {
        row.push([ data.getValue(i, 1 + 2 * j), data.getValue(i, 2 + 2 * j) ]);
      }
    }
    if (ret.length > 0 && row[0] < ret[ret.length - 1][0]) {
      outOfOrder = true;
    }
    ret.push(row);
  }

  if (outOfOrder) {
    console.warn("DataTable is out of order; order it correctly to speed loading.");
    ret.sort(function(a,b) { return a[0] - b[0]; });
  }
  this.rawData_ = ret;

  if (annotations.length > 0) {
    this.setAnnotations(annotations, true);
  }
  this.attributes_.reparseSeries();
};

/**
 * Signals to plugins that the chart data has updated.
 * This happens after the data has updated but before the chart has redrawn.
 */
Dygraph.prototype.cascadeDataDidUpdateEvent_ = function() {
  // TODO(danvk): there are some issues checking xAxisRange() and using
  // toDomCoords from handlers of this event. The visible range should be set
  // when the chart is drawn, not derived from the data.
  this.cascadeEvents_('dataDidUpdate', {});
};

/**
 * Get the CSV data. If it's in a function, call that function. If it's in a
 * file, do an XMLHttpRequest to get it.
 * @private
 */
Dygraph.prototype.start_ = function() {
  var data = this.file_;

  // Functions can return references of all other types.
  if (typeof data == 'function') {
    data = data();
  }

  if (Dygraph.isArrayLike(data)) {
    this.rawData_ = this.parseArray_(data);
    this.cascadeDataDidUpdateEvent_();
    this.predraw_();
  } else if (typeof data == 'object' &&
             typeof data.getColumnRange == 'function') {
    // must be a DataTable from gviz.
    this.parseDataTable_(data);
    this.cascadeDataDidUpdateEvent_();
    this.predraw_();
  } else if (typeof data == 'string') {
    // Heuristic: a newline means it's CSV data. Otherwise it's an URL.
    var line_delimiter = Dygraph.detectLineDelimiter(data);
    if (line_delimiter) {
      this.loadedEvent_(data);
    } else {
      // REMOVE_FOR_IE
      var req;
      if (window.XMLHttpRequest) {
        // Firefox, Opera, IE7, and other browsers will use the native object
        req = new XMLHttpRequest();
      } else {
        // IE 5 and 6 will use the ActiveX control
        req = new ActiveXObject("Microsoft.XMLHTTP");
      }

      var caller = this;
      req.onreadystatechange = function () {
        if (req.readyState == 4) {
          if (req.status === 200 ||  // Normal http
              req.status === 0) {    // Chrome w/ --allow-file-access-from-files
            caller.loadedEvent_(req.responseText);
          }
        }
      };

      req.open("GET", data, true);
      req.send(null);
    }
  } else {
    console.error("Unknown data format: " + (typeof data));
  }
};

/**
 * Changes various properties of the graph. These can include:
 * <ul>
 * <li>file: changes the source data for the graph</li>
 * <li>errorBars: changes whether the data contains stddev</li>
 * </ul>
 *
 * There's a huge variety of options that can be passed to this method. For a
 * full list, see http://dygraphs.com/options.html.
 *
 * @param {Object} input_attrs The new properties and values
 * @param {boolean} block_redraw Usually the chart is redrawn after every
 *     call to updateOptions(). If you know better, you can pass true to
 *     explicitly block the redraw. This can be useful for chaining
 *     updateOptions() calls, avoiding the occasional infinite loop and
 *     preventing redraws when it's not necessary (e.g. when updating a
 *     callback).
 */
Dygraph.prototype.updateOptions = function(input_attrs, block_redraw) {
  if (typeof(block_redraw) == 'undefined') block_redraw = false;

  // mapLegacyOptions_ drops the "file" parameter as a convenience to us.
  var file = input_attrs.file;
  var attrs = Dygraph.mapLegacyOptions_(input_attrs);

  // TODO(danvk): this is a mess. Move these options into attr_.
  if ('rollPeriod' in attrs) {
    this.rollPeriod_ = attrs.rollPeriod;
  }
  if ('dateWindow' in attrs) {
    this.dateWindow_ = attrs.dateWindow;
    if (!('isZoomedIgnoreProgrammaticZoom' in attrs)) {
      this.zoomed_x_ = (attrs.dateWindow !== null);
    }
  }
  if ('valueRange' in attrs && !('isZoomedIgnoreProgrammaticZoom' in attrs)) {
    this.zoomed_y_ = (attrs.valueRange !== null);
  }

  // TODO(danvk): validate per-series options.
  // Supported:
  // strokeWidth
  // pointSize
  // drawPoints
  // highlightCircleSize

  // Check if this set options will require new points.
  var requiresNewPoints = Dygraph.isPixelChangingOptionList(this.attr_("labels"), attrs);

  Dygraph.updateDeep(this.user_attrs_, attrs);

  this.attributes_.reparseSeries();

  if (file) {
    // This event indicates that the data is about to change, but hasn't yet.
    // TODO(danvk): support cancelation of the update via this event.
    this.cascadeEvents_('dataWillUpdate', {});

    this.file_ = file;
    if (!block_redraw) this.start_();
  } else {
    if (!block_redraw) {
      if (requiresNewPoints) {
        this.predraw_();
      } else {
        this.renderGraph_(false);
      }
    }
  }
};

/**
 * Returns a copy of the options with deprecated names converted into current
 * names. Also drops the (potentially-large) 'file' attribute. If the caller is
 * interested in that, they should save a copy before calling this.
 * @private
 */
Dygraph.mapLegacyOptions_ = function(attrs) {
  var my_attrs = {};
  for (var k in attrs) {
    if (!attrs.hasOwnProperty(k)) continue;
    if (k == 'file') continue;
    if (attrs.hasOwnProperty(k)) my_attrs[k] = attrs[k];
  }

  var set = function(axis, opt, value) {
    if (!my_attrs.axes) my_attrs.axes = {};
    if (!my_attrs.axes[axis]) my_attrs.axes[axis] = {};
    my_attrs.axes[axis][opt] = value;
  };
  var map = function(opt, axis, new_opt) {
    if (typeof(attrs[opt]) != 'undefined') {
      console.warn("Option " + opt + " is deprecated. Use the " +
          new_opt + " option for the " + axis + " axis instead. " +
          "(e.g. { axes : { " + axis + " : { " + new_opt + " : ... } } } " +
          "(see http://dygraphs.com/per-axis.html for more information.");
      set(axis, new_opt, attrs[opt]);
      delete my_attrs[opt];
    }
  };

  // This maps, e.g., xValueFormater -> axes: { x: { valueFormatter: ... } }
  map('xValueFormatter', 'x', 'valueFormatter');
  map('pixelsPerXLabel', 'x', 'pixelsPerLabel');
  map('xAxisLabelFormatter', 'x', 'axisLabelFormatter');
  map('xTicker', 'x', 'ticker');
  map('yValueFormatter', 'y', 'valueFormatter');
  map('pixelsPerYLabel', 'y', 'pixelsPerLabel');
  map('yAxisLabelFormatter', 'y', 'axisLabelFormatter');
  map('yTicker', 'y', 'ticker');
  map('drawXGrid', 'x', 'drawGrid');
  map('drawXAxis', 'x', 'drawAxis');
  map('drawYGrid', 'y', 'drawGrid');
  map('drawYAxis', 'y', 'drawAxis');
  map('xAxisLabelWidth', 'x', 'axisLabelWidth');
  map('yAxisLabelWidth', 'y', 'axisLabelWidth');
  return my_attrs;
};

/**
 * Resizes the dygraph. If no parameters are specified, resizes to fill the
 * containing div (which has presumably changed size since the dygraph was
 * instantiated. If the width/height are specified, the div will be resized.
 *
 * This is far more efficient than destroying and re-instantiating a
 * Dygraph, since it doesn't have to reparse the underlying data.
 *
 * @param {number} width Width (in pixels)
 * @param {number} height Height (in pixels)
 */
Dygraph.prototype.resize = function(width, height) {
  if (this.resize_lock) {
    return;
  }
  this.resize_lock = true;

  if ((width === null) != (height === null)) {
    console.warn("Dygraph.resize() should be called with zero parameters or " +
                 "two non-NULL parameters. Pretending it was zero.");
    width = height = null;
  }

  var old_width = this.width_;
  var old_height = this.height_;

  if (width) {
    this.maindiv_.style.width = width + "px";
    this.maindiv_.style.height = height + "px";
    this.width_ = width;
    this.height_ = height;
  } else {
    this.width_ = this.maindiv_.clientWidth;
    this.height_ = this.maindiv_.clientHeight;
  }

  if (old_width != this.width_ || old_height != this.height_) {
    // Resizing a canvas erases it, even when the size doesn't change, so
    // any resize needs to be followed by a redraw.
    this.resizeElements_();
    this.predraw_();
  }

  this.resize_lock = false;
};

/**
 * Adjusts the number of points in the rolling average. Updates the graph to
 * reflect the new averaging period.
 * @param {number} length Number of points over which to average the data.
 */
Dygraph.prototype.adjustRoll = function(length) {
  this.rollPeriod_ = length;
  this.predraw_();
};

/**
 * Returns a boolean array of visibility statuses.
 */
Dygraph.prototype.visibility = function() {
  // Do lazy-initialization, so that this happens after we know the number of
  // data series.
  if (!this.getOption("visibility")) {
    this.attrs_.visibility = [];
  }
  // TODO(danvk): it looks like this could go into an infinite loop w/ user_attrs.
  while (this.getOption("visibility").length < this.numColumns() - 1) {
    this.attrs_.visibility.push(true);
  }
  return this.getOption("visibility");
};

/**
 * Changes the visiblity of a series.
 *
 * @param {number} num the series index
 * @param {boolean} value true or false, identifying the visibility.
 */
Dygraph.prototype.setVisibility = function(num, value) {
  var x = this.visibility();
  if (num < 0 || num >= x.length) {
    console.warn("invalid series number in setVisibility: " + num);
  } else {
    x[num] = value;
    this.predraw_();
  }
};

/**
 * How large of an area will the dygraph render itself in?
 * This is used for testing.
 * @return A {width: w, height: h} object.
 * @private
 */
Dygraph.prototype.size = function() {
  return { width: this.width_, height: this.height_ };
};

/**
 * Update the list of annotations and redraw the chart.
 * See dygraphs.com/annotations.html for more info on how to use annotations.
 * @param ann {Array} An array of annotation objects.
 * @param suppressDraw {Boolean} Set to "true" to block chart redraw (optional).
 */
Dygraph.prototype.setAnnotations = function(ann, suppressDraw) {
  // Only add the annotation CSS rule once we know it will be used.
  Dygraph.addAnnotationRule();
  this.annotations_ = ann;
  if (!this.layout_) {
    console.warn("Tried to setAnnotations before dygraph was ready. " +
                 "Try setting them in a ready() block. See " +
                 "dygraphs.com/tests/annotation.html");
    return;
  }

  this.layout_.setAnnotations(this.annotations_);
  if (!suppressDraw) {
    this.predraw_();
  }
};

/**
 * Return the list of annotations.
 */
Dygraph.prototype.annotations = function() {
  return this.annotations_;
};

/**
 * Get the list of label names for this graph. The first column is the
 * x-axis, so the data series names start at index 1.
 *
 * Returns null when labels have not yet been defined.
 */
Dygraph.prototype.getLabels = function() {
  var labels = this.attr_("labels");
  return labels ? labels.slice() : null;
};

/**
 * Get the index of a series (column) given its name. The first column is the
 * x-axis, so the data series start with index 1.
 */
Dygraph.prototype.indexFromSetName = function(name) {
  return this.setIndexByName_[name];
};

/**
 * Trigger a callback when the dygraph has drawn itself and is ready to be
 * manipulated. This is primarily useful when dygraphs has to do an XHR for the
 * data (i.e. a URL is passed as the data source) and the chart is drawn
 * asynchronously. If the chart has already drawn, the callback will fire
 * immediately.
 *
 * This is a good place to call setAnnotation().
 *
 * @param {function(!Dygraph)} callback The callback to trigger when the chart
 *     is ready.
 */
Dygraph.prototype.ready = function(callback) {
  if (this.is_initial_draw_) {
    this.readyFns_.push(callback);
  } else {
    callback.call(this, this);
  }
};

/**
 * @private
 * Adds a default style for the annotation CSS classes to the document. This is
 * only executed when annotations are actually used. It is designed to only be
 * called once -- all calls after the first will return immediately.
 */
Dygraph.addAnnotationRule = function() {
  // TODO(danvk): move this function into plugins/annotations.js?
  if (Dygraph.addedAnnotationCSS) return;

  var rule = "border: 1px solid black; " +
             "background-color: white; " +
             "text-align: center;";

  var styleSheetElement = document.createElement("style");
  styleSheetElement.type = "text/css";
  document.getElementsByTagName("head")[0].appendChild(styleSheetElement);

  // Find the first style sheet that we can access.
  // We may not add a rule to a style sheet from another domain for security
  // reasons. This sometimes comes up when using gviz, since the Google gviz JS
  // adds its own style sheets from google.com.
  for (var i = 0; i < document.styleSheets.length; i++) {
    if (document.styleSheets[i].disabled) continue;
    var mysheet = document.styleSheets[i];
    try {
      if (mysheet.insertRule) {  // Firefox
        var idx = mysheet.cssRules ? mysheet.cssRules.length : 0;
        mysheet.insertRule(".dygraphDefaultAnnotation { " + rule + " }", idx);
      } else if (mysheet.addRule) {  // IE
        mysheet.addRule(".dygraphDefaultAnnotation", rule);
      }
      Dygraph.addedAnnotationCSS = true;
      return;
    } catch(err) {
      // Was likely a security exception.
    }
  }

  console.warn("Unable to add default annotation CSS rule; display may be off.");
};

if (typeof exports === "object" && typeof module !== "undefined") {
  module.exports = Dygraph;
}

return Dygraph;

})();
