
// Don't spew on in the console window when we build
if ( navigator.userAgent.indexOf("PhantomJS") >= 0 ) {
	jQuery.migrateMute = true;
}

function expectWarning( name, expected, fn ) {
	if ( !fn ) {
		fn = expected;
		expected = null;
	}
	jQuery.migrateReset();
	fn();

	// Special-case for 0 warnings expected
	if ( expected === 0 ) {
		deepEqual( jQuery.migrateWarnings, [], name + ": did not warn" );

	// Simple numeric equality assertion for warnings matching an explicit count
	} else if ( expected && jQuery.migrateWarnings.length === expected ) {
		equal( jQuery.migrateWarnings.length, expected, name + ": warned" );

	// Simple ok assertion when we saw at least one warning and weren't looking for an explict count
	} else if ( !expected && jQuery.migrateWarnings.length ) {
		ok( true, name + ": warned" );

	// Failure; use deepEqual to show the warnings that *were* generated and the expectation
	} else {
		deepEqual( jQuery.migrateWarnings, "<warnings: " + ( expected || "1+" ) + ">", name + ": warned" );
	}
}

function expectNoWarning( name, expected, fn ) {
	// Expected is present only for signature compatibility with expectWarning
	return expectWarning( name, 0, fn || expected );
}
