/* http://keith-wood.name/timeEntry.html
   Time entry for jQuery v1.3.0.
   Written by Keith Wood (kbwood@virginbroadband.com.au) June 2007.
   Dual licensed under the GPL (http://dev.jquery.com/browser/trunk/jquery/GPL-LICENSE.txt) and 
   MIT (http://dev.jquery.com/browser/trunk/jquery/MIT-LICENSE.txt) licenses. 
   Please attribute the author if you use it. */

/* Turn an input field into an entry point for a time value.
   The time can be entered via directly typing the value,
   via the arrow keys, or via spinner buttons.
   It is configurable to show 12 or 24-hour time, to show or hide seconds,
   to enforce a minimum and/or maximum time, to change the spinner image,
   and to constrain the time to steps, e.g. only on the quarter hours.
   Attach it with $('input selector').timeEntry(); for default settings,
   or configure it with options like:
   $('input selector').timeEntry(
      {spinnerImage: 'timeEntry2.png', spinnerSize: [20, 20, 0]}); */

(function($) { // Hide scope, no $ conflict

/* TimeEntry manager.
   Use the singleton instance of this class, $.timeEntry, to interact with the time entry
   functionality. Settings for (groups of) fields are maintained in an instance object
   (TimeEntryInstance), allowing multiple different settings on the same page. */
function TimeEntry() {
	this._nextId = 0; // Next ID for a time entry instance
	this._inst = []; // List of instances indexed by ID
	this._disabledInputs = []; // List of time entry inputs that have been disabled
	this.regional = []; // Available regional settings, indexed by language code
	this.regional[''] = { // Default regional settings
		show24Hours: false, // True to use 24 hour time, false for 12 hour (AM/PM)
		separator: ':', // The separator between time fields
		ampmPrefix: '', // The separator before the AM/PM text
		ampmNames: ['AM', 'PM'], // Names of morning/evening markers
		spinnerTexts: ['Now', 'Previous field', 'Next field', 'Increment', 'Decrement']
		// The popup texts for the spinner image areas
	};
	this._defaults = {
		appendText: '', // Display text following the input box, e.g. showing the format
		showSeconds: false, // True to show seconds as well, false for hours/minutes only
		timeSteps: [1, 1, 1], // Steps for each of hours/minutes/seconds when incrementing/decrementing
		initialField: 0, // The field to highlight initially, 0 = hours, 1 = minutes, ...
		useMouseWheel: true, // True to use mouse wheel for increment/decrement if possible,
			// false to never use it
		minTime: null, // The earliest selectable time, or null for no limit
		maxTime: null, // The latest selectable time, or null for no limit
		spinnerImage: 'timeEntry.png', // The URL of the images to use for the time spinner
			// Six images packed horizontally for normal and then each button pressed
		spinnerSize: [20, 20, 8], // The width and height of the spinner image,
			// and size of centre button for current time
		spinnerIncDecOnly: false, // True for increment/decrement buttons only, false for all
		spinnerRepeat: [500, 250], // Initial and subsequent waits in milliseconds
			// for repeats on the spinner buttons
		beforeShow: null // Function that takes an input field and
			// returns a set of custom settings for the time entry
	};
	$.extend(this._defaults, this.regional['']);
}

$.extend(TimeEntry.prototype, {
	/* Class name added to elements to indicate already configured with time entry. */
	markerClassName: 'hasTimeEntry',
	
	/* Register a new time entry instance - with custom settings. */
	_register: function(inst) {
		var id = this._nextId++;
		this._inst[id] = inst;
		return id;
	},

	/* Retrieve a particular time entry instance based on its ID. */
	_getInst: function(id) {
		return this._inst[id] || id;
	},

	/* Override the default settings for all instances of the time entry.
	   @param  settings  object - the new settings to use as defaults (anonymous object)
	   @return void */
	setDefaults: function(settings) {
		extendRemove(this._defaults, settings || {});
	},

	/* Initialise time entry. */
	_doFocus: function(target) {
		var input = (target.nodeName && target.nodeName.toLowerCase() == 'input' ? target : this);
		if ($.timeEntry._lastInput == input) { // already here
			return;
		}
		if ($.timeEntry._isDisabledTimeEntry(input)) {
			return;
		}
		var inst = $.timeEntry._getInst(input._timeId);
		inst._input = $(input);
		$.timeEntry._lastInput = input;
		$.timeEntry._blurredInput = null;
		var beforeShow = inst._get('beforeShow');
		extendRemove(inst._settings, (beforeShow ? beforeShow(input) : {}));
		inst._parseTime();
	},

	/* Note that the field has been exited. */
	_doBlur: function(event) {
		$.timeEntry._blurredInput = $.timeEntry._lastInput;
		$.timeEntry._lastInput = null;
	},

	/* Select appropriate field portion on double click. */
	_doDblClick: function(event) {
		var input = event.target;
		var inst = $.timeEntry._getInst(input._timeId);
		var fieldSize = inst._get('separator').length + 2;
		inst._field = 0;
		if ($.browser.mozilla) { // calc from character offset
			var offset = event.rangeOffset;
			inst._field = (offset > Math.max(1, inst._secondField) * fieldSize + 2 ?
				inst._ampmField : Math.floor(offset / fieldSize));
		}
		else if ($.browser.msie) { // check against bounding boxes
			var value = input.value;
			for (var field = 0; field <= Math.max(1, inst._secondField, inst._ampmField); field++) {
				var end = (field != inst._ampmField ? (field * fieldSize) + 2 :
					(inst._ampmField * fieldSize) + inst._get('ampmPrefix').length +
					inst._get('ampmNames')[0].length);
				input.value = value.substring(0, end); // trim to this size
				var range = input.createTextRange();
				if (event.offsetX < range.boundingWidth) { // and compare
					inst._field = field;
					break;
				}
			}
			input.value = value; // restore original value
		}
		else if ($.browser.opera || $.browser.safari) { // use input select range
			var value = input.value;
			for (var field = 0; field <= Math.max(1, inst._secondField, inst._ampmField); field++) {
				var start = (field != inst._ampmField ? (field * fieldSize) :
					(inst._ampmField * fieldSize) + inst._get('ampmPrefix').length);
				if (start >= input.selectionStart) {
					inst._field = field;
					break;
				}
			}
		}
		inst._showField();
	},

	/* Handle keystrokes in the field. */
	_doKeyDown: function(event) {
		if (event.keyCode >= 48) { // >= '0'
			return true;
		}
		var inst = $.timeEntry._getInst(this._timeId);
		switch (event.keyCode) {
			case 9: return (event.shiftKey ?
						// move to previous time field, or out if at the beginning
						inst._previousField(true) :
						// move to next time field, or out if at the end
						inst._nextField(true));
			case 35: if (event.ctrlKey) { // clear time on ctrl+end
						inst._setValue('');
					}
					else { // last field on end
						inst._field = Math.max(1, inst._secondField, inst._ampmField);
						inst._adjustField(0);
					}
					break;
			case 36: if (event.ctrlKey) { // current time on ctrl+home
						inst._setTime();
					}
					else { // first field on home
						inst._field = 0;
						inst._adjustField(0);
					}
					break;
			case 37: inst._previousField(false); break; // previous field on left
			case 38: inst._adjustField(+1); break; // increment time field on up
			case 39: inst._nextField(false); break; // next field on right
			case 40: inst._adjustField(-1); break; // decrement time field on down
			case 46: inst._setValue(''); break; // clear time on delete
		}
		return false;
	},

	/* Disallow unwanted characters. */
	_doKeyPress: function(event) {
		var chr = String.fromCharCode(event.charCode == undefined ? event.keyCode : event.charCode);
		if (chr < ' ') {
			return true;
		}
		var inst = $.timeEntry._getInst(this._timeId);
		inst._handleKeyPress(chr);
		return false;
	},

	/* Increment/decrement on mouse wheel activity. */
	_doMouseWheel: function(event, delta) {
		delta = ($.browser.opera ? -delta / Math.abs(delta) : delta);
		var inst = $.timeEntry._getInst(this._timeId);
		inst._adjustField(delta);
		event.preventDefault();
	},

	/* Attach the time entry handler to an input field. */
	_connectTimeEntry: function(target, inst) {
		var input = $(target);
		if (input.is('.' + this.markerClassName)) {
			return;
		}
		var spinnerImage = inst._get('spinnerImage');
		var spinnerText = inst._get('spinnerText');
		var spinnerSize = inst._get('spinnerSize');
		var appendText = inst._get('appendText');
		var spinner = (!spinnerImage ? null : 
			$('<span class="timeEntry_control" _timeid="' + inst._id +
			'" style="display: inline-block; background: url(\'' + spinnerImage + '\') 0 0 no-repeat; ' +
			'width: ' + spinnerSize[0] + 'px; height: ' + spinnerSize[1] + 'px;' +
			($.browser.mozilla ? ' padding-left: ' + spinnerSize[0] + 
			'px; padding-top: ' + (spinnerSize[1] - 18) + 'px;' : '') + '"></span>'));
		input.wrap('<span class="timeEntry_wrap"></span>').
			after(appendText ? '<span class="timeEntry_append">' + appendText + '</span>' : '').
			after(spinner || '');
		input.addClass(this.markerClassName).focus(this._doFocus).blur(this._doBlur).
			dblclick(this._doDblClick).keydown(this._doKeyDown).keypress(this._doKeyPress);
		// check pastes
		if ($.browser.mozilla) {
			input.bind('input', function(event) { inst._parseTime(); });
		}
		if ($.browser.msie) {
			input.bind('paste', function(event) { 
				setTimeout(function() { inst._parseTime(); }, 1); });
		}
		// allow mouse wheel usage
		if (inst._get('useMouseWheel') && $.fn.mousewheel) {
			input.mousewheel(this._doMouseWheel);
		}
		input[0]._timeId = inst._id;
		if (spinner) {
			spinner.mousedown(this._handleSpinner).mouseup(this._endSpinner).
				mouseout(this._endSpinner).mousemove(this._describeSpinner);
			spinner[0]._timeId = inst._id;
		}
	},

	/* Enable a time entry input and any associated spinner.
	   @param  input  element - single input field
	   @return void */
	_enableTimeEntry: function(input) {
		this._enableDisable(input, false);
	},

	/* Disable a time entry input and any associated spinner.
	   @param  input  element - single input field
	   @return void */
	_disableTimeEntry: function(input) {
		this._enableDisable(input, true);
	},

	/* Enable or disable a time entry input and any associated spinner.
	   @param  input    element - single input field
	   @param  disable  boolean - true to disable, false to enable
	   @return void */
	_enableDisable: function(input, disable) {
		var inst = $.timeEntry._getInst(input._timeId);
		if (!inst) {
			return;
		}
		input.disabled = disable;
		if (input.nextSibling && input.nextSibling.nodeName.toLowerCase() == 'span') {
			$.timeEntry._changeSpinner(inst, input.nextSibling, (disable ? 5 : -1));
		}
		$.timeEntry._disabledInputs = $.map($.timeEntry._disabledInputs,
			function(value) { return (value == input ? null : value); }); // delete entry
		if (disable) {
			$.timeEntry._disabledInputs[$.timeEntry._disabledInputs.length] = input;
		}
	},

	/* Check whether an input field has been disabled.
	   @param  input  element - input field to check
	   @return true if this field has been disabled, false if it is enabled */
	_isDisabledTimeEntry: function(input) {
		for (var i = 0; i < this._disabledInputs.length; i++) {
			if (this._disabledInputs[i] == input) {
				return true;
			}
		}
		return false;
	},

	/* Reconfigure the settings for a time entry field. */
	_changeTimeEntry: function(input, settings) {
		var inst = this._getInst(input._timeId);
		if (inst) {
			var currentTime = inst._extractTime();
			extendRemove(inst._settings, settings || {});
			if (currentTime) {
				inst._setTime(new Date(0, 0, 0, currentTime[0], currentTime[1], currentTime[2]));
			}
		}
	},

	/* Remove the time entry functionality from an input. */
	_destroyTimeEntry: function(input) {
		$input = $(input);
		if (!$input.is('.' + this.markerClassName)) {
			return;
		}
		input.parentNode.parentNode.replaceChild(input, input.parentNode);
		$input.removeClass(this.markerClassName).unbind('focus', this._doFocus).
			unbind('blur', this._doBlur).unbind('dblclick', this._doDblClick).
			unbind('keydown', this._doKeyDown).unbind('keypress', this._doKeyPress);
		// check pastes
		if ($.browser.mozilla) {
			$input.unbind('input');
		}
		if ($.browser.msie) {
			$input.unbind('paste');
		}
		if ($.fn.mousewheel) {
			$input.unmousewheel();
		}
		this._inst[input._timeId] = null;
		input._timeId = undefined;
		this._disabledInputs = $.map(this._disabledInputs,
			function(value) { return (value == input ? null : value); }); // delete entry
	},

	/* Initialise the current time for a time entry input field.
	   @param  input  element - input field to update
	   @param  time   Date - the new time (year/month/day ignored) or null for now */
	_setTimeTimeEntry: function(input, time) {
		var inst = this._getInst(input._timeId);
		if (inst) {
			inst._input = $(input);
			inst._setTime(time);
		}
	},

	/* Retrieve the current time for a time entry input field.
	   @param  input  element - input field to update
	   @return Date with the set time (year/month/day zero) or null if none */
	_getTimeTimeEntry: function(input) {
		var inst = this._getInst(input._timeId);
		var currentTime = (inst ? inst._extractTime() : null);
		return (!currentTime ? null :
			new Date(0, 0, 0, currentTime[0], currentTime[1], currentTime[2]));
	},

	/* Change the title based on position within the spinner. */
	_describeSpinner: function(event) {
		var spinner = $.timeEntry._getSpinnerTarget(event);
		var inst = $.timeEntry._getInst(spinner._timeId);
		spinner.title = inst._get('spinnerTexts')[$.timeEntry._getSpinnerRegion(inst, event)];
	},

	/* Handle a click on the spinner. */
	_handleSpinner: function(event) {
		var spinner = $.timeEntry._getSpinnerTarget(event);
		var input = spinner.previousSibling;
		if ($.timeEntry._isDisabledTimeEntry(input)) {
			return;
		}
		if (input == $.timeEntry._blurredInput) {
			$.timeEntry._lastInput = input;
			$.timeEntry._blurredInput = null;
		}
		var inst = $.timeEntry._getInst(input._timeId);
		$.timeEntry._doFocus(input);
		var region = $.timeEntry._getSpinnerRegion(inst, event);
		$.timeEntry._changeSpinner(inst, spinner, region);
		$.timeEntry._actionSpinner(inst, region);
		var spinnerRepeat = inst._get('spinnerRepeat');
		if (region >= 3 && spinnerRepeat[0]) { // repeat increment/decrement
			$.timeEntry._timer = setTimeout(
				function() { $.timeEntry._repeatSpinner(inst, region); },
				spinnerRepeat[0]);
			$(spinner).one('mouseout', $.timeEntry._releaseSpinner).
				one('mouseup', $.timeEntry._releaseSpinner);
		}
	},

	/* Action a click on the spinner. */
	_actionSpinner: function(inst, region) {
		switch (region) {
			case 0: inst._setTime(); break;
			case 1: inst._previousField(false); break;
			case 2: inst._nextField(false); break;
			case 3: inst._adjustField(+1); break;
			case 4: inst._adjustField(-1); break;
		}
	},

	/* Repeat a click on the spinner. */
	_repeatSpinner: function(inst, region) {
		$.timeEntry._lastInput = $.timeEntry._blurredInput;
		this._actionSpinner(inst, region);
		this._timer = setTimeout(
			function() { $.timeEntry._repeatSpinner(inst, region); },
			inst._get('spinnerRepeat')[1]);
	},

	/* Stop a spinner repeat. */
	_releaseSpinner: function(event) {
		clearTimeout($.timeEntry._timer);
	},

	/* Tidy up after a spinner click. */
	_endSpinner: function(event) {
		var spinner = $.timeEntry._getSpinnerTarget(event);
		var inst = $.timeEntry._getInst(spinner._timeId);
		if (!$.timeEntry._isDisabledTimeEntry(spinner.previousSibling)) {
			$.timeEntry._changeSpinner(inst, spinner, -1);
		}
		if (!$.browser.opera) {
			$.timeEntry._lastInput = $.timeEntry._blurredInput;
		}
		if ($.timeEntry._lastInput) {
			inst._showField();
		}
	},

	/* Retrieve the spinner from the event. */
	_getSpinnerTarget: function(event) {
		return (event.target ? event.target : event.srcElement);
	},

	/* Determine which "button" within the spinner was clicked. */
	_getSpinnerRegion: function(inst, event) {
		var spinner = this._getSpinnerTarget(event);
		var pos = this._findPos(spinner);
		var scrolled = this._findScroll(spinner);
		var spinnerIncDecOnly = inst._get('spinnerIncDecOnly');
		var left = (spinnerIncDecOnly ? 99 :
			event.clientX + scrolled[0] - pos[0] - ($.browser.msie ? 1 : 0));
		var top = event.clientY + scrolled[1] - pos[1] - ($.browser.msie ? 1 : 0);
		var spinnerSize = inst._get('spinnerSize');
		var right = (spinnerIncDecOnly ? 99 : spinnerSize[0] - left);
		var bottom = spinnerSize[1] - top;
		if (spinnerSize[2] > 0 && Math.abs(left - right) <= spinnerSize[2] &&
				Math.abs(top - bottom) <= spinnerSize[2]) {
			return 0; // centre button
		}
		var min = Math.min(left, top, right, bottom);
		return (min == left ? 1 : (min == right ? 2 : (min == top ? 3 : 4))); // nearest edge
	},

	/* Change the spinner image depending on button clicked. */
	_changeSpinner: function(inst, spinner, region) {
		$(spinner).css('background-position',
			'-' + ((region + 1) * inst._get('spinnerSize')[0]) + 'px 0px');
	},

	/* Find an object's position on the screen. */
	_findPos: function(obj) {
		var curLeft = curTop = 0;
		if (obj.offsetParent) {
			curLeft = obj.offsetLeft;
			curTop = obj.offsetTop;
			while (obj = obj.offsetParent) {
				var origCurLeft = curLeft;
				curLeft += obj.offsetLeft;
				if (curLeft < 0) {
					curLeft = origCurLeft;
				}
				curTop += obj.offsetTop;
			}
		}
		return [curLeft, curTop];
	},

	/* Find an object's scroll offset on the screen. */
	_findScroll: function(obj) {
		var isFixed = false;
		$(obj).parents().each(function() {
			isFixed |= $(this).css('position') == 'fixed';
		});
		if (isFixed && !$.browser.opera) {
			return [0, 0];
		}
		var scrollLeft = ($.browser.opera ? document.body.scrollLeft : obj.scrollLeft);
		var scrollTop = ($.browser.opera ? document.body.scrollTop : obj.scrollTop);;
		if (!$.browser.opera) {
			while (obj = obj.parentNode) {
				scrollLeft += obj.scrollLeft || 0;
				scrollTop += obj.scrollTop || 0;
			}
		}
		return [scrollLeft, scrollTop];
	}
});

/* Individualised settings for time entries applied to one or more related inputs.
   Instances are managed and manipulated through the TimeEntry manager. */
function TimeEntryInstance(settings) {
	this._id = $.timeEntry._register(this);
	this._selectedHour = 0; // The currently selected hour
	this._selectedMinute = 0; // The currently selected minute
	this._selectedSecond = 0; // The currently selected second
	this._input = null; // The attached input field
	// customise the time entry object - uses manager defaults if not overridden
	this._settings = extendRemove({}, settings || {}); // clone
}

$.extend(TimeEntryInstance.prototype, {
	/* Get a setting value, defaulting if necessary. */
	_get: function(name) {
		return (this._settings[name] != null ? this._settings[name] : $.timeEntry._defaults[name]);
	},

	/* Extract the time value from the input field, or default to now. */
	_parseTime: function() {
		var currentTime = this._extractTime();
		var showSeconds = this._get('showSeconds');
		if (currentTime) {
			this._selectedHour = currentTime[0];
			this._selectedMinute = currentTime[1];
			this._selectedSecond = currentTime[2];
		}
		else {
			var now = this._constrainTime();
			this._selectedHour = now[0];
			this._selectedMinute = now[1];
			this._selectedSecond = (showSeconds ? now[2] : 0);
		}
		this._secondField = (showSeconds ? 2 : -1);
		this._ampmField = (this._get('show24Hours') ? -1 : (showSeconds ? 3 : 2));
		this._lastChr = '';
		this._field = Math.max(0, Math.min(
			Math.max(1, this._secondField, this._ampmField), this._get('initialField')));
		if (this._input.val() != '') {
			this._showTime();
		}
	},

	/* Extract the time value from the input field as an array of values, or default to null. */
	_extractTime: function() {
		var value = (this._input ? this._input.val() : '');
		var separator = this._get('separator');
		var currentTime = value.split(separator);
		if (separator == '' && value != '') {
			currentTime[0] = value.substring(0, 2);
			currentTime[1] = value.substring(2, 4);
			currentTime[2] = value.substring(4, 6);
		}
		var ampmNames = this._get('ampmNames');
		if (currentTime.length >= 2) {
			var isAM = (value.indexOf(ampmNames[0]) > -1);
			var isPM = (value.indexOf(ampmNames[1]) > -1);
			var hour = parseInt(currentTime[0], 10);
			hour = (isNaN(hour) ? 0 : hour);
			hour = ((isAM || isPM) && hour == 12 ? 0 : hour) + (isPM ? 12 : 0);
			var minute = parseInt(currentTime[1], 10);
			minute = (isNaN(minute) ? 0 : minute);
			var second = (currentTime.length >= 3 ?
				parseInt(currentTime[2], 10) : 0);
			second = (isNaN(second) || !this._get('showSeconds') ? 0 : second);
			return [hour, minute, second];
		} 
		return null;
	},

	/* Constrain the given/current time to the time steps. */
	_constrainTime: function(fields) {
		var specified = (fields != null);
		if (!specified) {
			var now = new Date();
			fields = [now.getHours(), now.getMinutes(), now.getSeconds()];
		}
		var reset = false;
		var timeSteps = this._get('timeSteps');
		for (var i = 0; i < timeSteps.length; i++) {
			if (reset) {
				fields[i] = 0;
			}
			else if (timeSteps[i] > 1) {
				fields[i] = Math.round(fields[i] / timeSteps[i]) * timeSteps[i];
				reset = !specified;
			}
		}
		return fields;
	},

	/* Set the selected time into the input field. */
	_showTime: function() {
		var show24Hours = this._get('show24Hours');
		var separator = this._get('separator');
		var currentTime = (this._formatNumber(show24Hours ? this._selectedHour :
			((this._selectedHour + 11) % 12) + 1) + separator +
			this._formatNumber(this._selectedMinute) +
			(this._get('showSeconds') ? separator + this._formatNumber(this._selectedSecond) : '') +
			(show24Hours ?  '' : this._get('ampmPrefix') +
			this._get('ampmNames')[(this._selectedHour < 12 ? 0 : 1)]));
		this._setValue(currentTime);
		this._showField();
	},

	/* Highlight the current time field. */
	_showField: function() {
		if (!this._input) {
			return;
		}
		var input = this._input[0];
		var separator = this._get('separator');
		var fieldSize = separator.length + 2;
		var start = (this._field != this._ampmField ? (this._field * fieldSize) :
			(this._ampmField * fieldSize) - separator.length + this._get('ampmPrefix').length);
		var end = start + (this._field != this._ampmField ? 2 : this._get('ampmNames')[0].length);
		if (input.setSelectionRange) { // Mozilla
			input.setSelectionRange(start, end);
		}
		else if (input.createTextRange) { // IE
			var range = input.createTextRange();
			range.moveStart('character', start);
			range.moveEnd('character', end - this._input.val().length);
			range.select();
		}
		if (!input.disabled) {
			input.focus();
		}
	},

	/* Ensure displayed single number has a leading zero. */
	_formatNumber: function(value) {
		return (value < 10 ? '0' : '') + value;
	},

	/* Update the input field and notify listeners. */
	_setValue: function(value) {
		this._input.val(value);
		this._input.trigger('change');
	},

	/* Move to previous field, or out of field altogether if appropriate (return  true). */
	_previousField: function(moveOut) {
		var atFirst = (this._input.val() == '' || this._field == 0);
		if (!atFirst) {
			this._field--;
		}
		this._showField();
		this._lastChr = '';
		return (atFirst && moveOut);
	},

	/* Move to next field, or out of field altogether if appropriate (return  true). */
	_nextField: function(moveOut) {
		var atLast = (this._input.val() == '' ||
			this._field == Math.max(1, this._secondField, this._ampmField));
		if (!atLast) {
			this._field++;
		}
		this._showField();
		this._lastChr = '';
		return (atLast && moveOut);
	},

	/* Update the current field in the direction indicated. */
	_adjustField: function(offset) {
		if (this._input.val() == '') {
			offset = 0;
		}
		var timeSteps = this._get('timeSteps');
		this._setTime(new Date(0, 0, 0,
			this._selectedHour + (this._field == 0 ? offset * timeSteps[0] : 0) +
			(this._field == this._ampmField ? offset * 12 : 0),
			this._selectedMinute + (this._field == 1 ? offset * timeSteps[1] : 0),
			this._selectedSecond + (this._field == this._secondField ? offset * timeSteps[2] : 0)));
	},

	/* Check against minimum/maximum and display time. */
	_setTime: function(time) {
		if (!time) { // default to now
			var now = this._constrainTime();
			time = new Date(0, 0, 0, now[0], now[1], now[2]);
		}
		// normalise to base date
		var time = this._normaliseTime(time);
		var minTime = this._normaliseTime(this._get('minTime'));
		var maxTime = this._normaliseTime(this._get('maxTime'));
		// ensure it is within the bounds set
		time = (minTime && time < minTime ? minTime :
			(maxTime && time > maxTime ? maxTime : time));
		this._selectedHour = time.getHours();
		this._selectedMinute = time.getMinutes();
		this._selectedSecond = time.getSeconds();
		this._showTime();
	},

	/* Normalise time object to a common date. */
	_normaliseTime: function(time) {
		if (!time) {
			return null;
		}
		time.setFullYear(2001);
		time.setMonth(1 - 1);
		time.setDate(26);
		return time;
	},

	/* Update time based on keystroke entered. */
	_handleKeyPress: function(chr) {
		if (chr == this._get('separator')) {
			this._nextField(false);
		}
		else if (chr >= '0' && chr <= '9') { // allow direct entry of time
			var value = (this._lastChr + chr) * 1;
			var hour = (this._field == 0 && ((this._get('show24Hours') && value < 24) ||
				(value >= 1 && value <= 12)) ? value : this._selectedHour);
			var minute = (this._field == 1 && value < 60 ? value : this._selectedMinute);
			var second = (this._field == this._secondField && value < 60 ?
				value : this._selectedSecond);
			var fields = this._constrainTime([hour, minute, second]);
			this._setTime(new Date(0, 0, 0, fields[0], fields[1], fields[2]));
			this._lastChr = chr;
		}
		else if (!this._get('show24Hours')) { // set am/pm based on first char of names
			var ampmNames = this._get('ampmNames');
			if ((chr == ampmNames[0].substring(0, 1).toLowerCase() &&
					this._selectedHour >= 12) ||
					(chr == ampmNames[1].substring(0, 1).toLowerCase() &&
					this._selectedHour < 12)) {
				var saveField = this._field;
				this._field = this._ampmField;
				this._adjustField(+1);
				this._field = saveField;
				this._showField();
			}
		}
	}
});

/* jQuery extend now ignores nulls! */
function extendRemove(target, props) {
	$.extend(target, props);
	for (var name in props) {
		if (props[name] == null) {
			target[name] = null;
		}
	}
	return target;
}

/* Attach the time entry functionality to a jQuery selection.
   @param  command  string - the command to run (optional, default 'attach')
   @param  options  object - the new settings to use for these countdown instances
   @return jQuery object - for chaining further calls */
$.fn.timeEntry = function(options) {
	var otherArgs = Array.prototype.slice.call(arguments, 1);
	if (typeof options == 'string' && (options == 'isDisabled' || options == 'getTime')) {
		return $.timeEntry['_' + options + 'TimeEntry'].apply($.timeEntry, [this[0]].concat(otherArgs));
	}
	return this.each(function() {
		var nodeName = this.nodeName.toLowerCase();
		if (nodeName == 'input') {
			if (typeof options == 'string') {
				$.timeEntry['_' + options + 'TimeEntry'].apply($.timeEntry, [this].concat(otherArgs));
			}
			else {
				// check for settings on the control itself - in namespace 'time:'
				var inlineSettings = null;
				for (attrName in $.timeEntry._defaults) {
					var attrValue = this.getAttribute('time:' + attrName);
					if (attrValue) {
						inlineSettings = inlineSettings || {};
						try {
							inlineSettings[attrName] = eval(attrValue);
						}
						catch (err) {
							inlineSettings[attrName] = attrValue;
						}
					}
				}
				var inst = (inst && !inlineSettings ? inst :
					new TimeEntryInstance(!inlineSettings ? options :
					$.extend(inlineSettings, options)));
				$.timeEntry._connectTimeEntry(this, inst);
			}
		} 
	});
};

/* Initialise the time entry functionality. */
$(document).ready(function() {
   $.timeEntry = new TimeEntry(); // singleton instance
});

})(jQuery);
