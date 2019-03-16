
var internalSwapCall = false;

// If this version of jQuery has .swap(), don't false-alarm on internal uses
if ( jQuery.swap ) {
	jQuery.each( [ "height", "width", "reliableMarginRight" ], function( _, name ) {
		var oldHook = jQuery.cssHooks[ name ] && jQuery.cssHooks[ name ].get;

		if ( oldHook ) {
			jQuery.cssHooks[ name ].get = function() {
				var ret;

				internalSwapCall = true;
				ret = oldHook.apply( this, arguments );
				internalSwapCall = false;
				return ret;
			};
		}
	});
}

jQuery.swap = function( elem, options, callback, args ) {
	var ret, name,
		old = {};

	if ( !internalSwapCall ) {
		migrateWarn( "jQuery.swap() is undocumented and deprecated" );
	}

	// Remember the old values, and insert the new ones
	for ( name in options ) {
		old[ name ] = elem.style[ name ];
		elem.style[ name ] = options[ name ];
	}

	ret = callback.apply( elem, args || [] );

	// Revert the old values
	for ( name in options ) {
		elem.style[ name ] = old[ name ];
	}

	return ret;
};
