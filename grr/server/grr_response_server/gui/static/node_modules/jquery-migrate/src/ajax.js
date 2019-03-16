
// Ensure that $.ajax gets the new parseJSON defined in core.js
jQuery.ajaxSetup({
	converters: {
		"text json": jQuery.parseJSON
	}
});
