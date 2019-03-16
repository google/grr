
module("css");

test( "jQuery.swap()", function( assert ) {
	assert.expect( 6 );

	var div = document.createElement( "div" );
	div.style.borderWidth = "4px";

	expectWarning( "External swap() call", function() {
		jQuery.swap( div, { borderRightWidth: "5px" }, function( arg ) {

			assert.equal( this.style.borderRightWidth, "5px", "style was changed" );
			assert.equal( arg, 42, "arg was passed" );

		}, [ 42 ] );
	});
	assert.equal( div.style.borderRightWidth, "4px", "style was restored" );

	expectNoWarning( "Internal swap() call", function() {
		var $fp = jQuery( "#firstp" ).width( "10em" ),
			width = $fp.width();

		assert.equal( $fp.hide().width(), width, "correct width" );
	});

});
