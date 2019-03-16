
TestManager = {
	/*
	 * Load a version of a file based on URL parameters.
	 *
	 *	dev		Uncompressed development version in the project /dist dir
	 *	min		Minified version in the project /dist dir
	 *	VER		Version from code.jquery.com, e.g.: git, 1.8.2.min or 1.7rc1
	 *	else	Full or relative path to be used for script src
	 */
	loadProject: function( projectName, defaultVersion, isSelf ) {
		var file,
			urlTag = this.projects[ projectName ].urlTag,
			matcher = new RegExp( "\\b" + urlTag + "=([^&]+)" ),
			projectRoot = isSelf ? ".." : "../../" + projectName,
			version = ( matcher.exec( document.location.search ) || {} )[1] || defaultVersion;

		if ( version === "dev" ) {
			file = projectRoot + "/dist/" + projectName + ".js";
		} else if ( version === "min" ) {
			file = projectRoot + "/dist/" + projectName + ".min.js";
		} else if ( /^[\w\.\-]+$/.test( version ) ) {
			file = "http://code.jquery.com/" + projectName + "-" + version + ".js";
		} else {
			file = version;
		}
		this.loaded.push({
			projectName: projectName,
			tag: version,
			file: file
		});

		// Prevents a jshint warning about eval-like behavior of document.write
		document["write"]( "<script src='" + file + "'></script>" );
	},
	init: function( projects ) {
		var p, project;

		this.projects = projects;
		this.loaded = [];

		// Set the list of projects, including the project version choices.
		for ( p in projects ) {
			project = projects[ p ];
			QUnit.config.urlConfig.push({
				label: p,
				id: project.urlTag,
				value: project.choices.split(",")
			});
		}
	}
};

/**
 * QUnit configuration
 */
// Max time for async tests until it aborts test
// and start()'s the next test.
QUnit.config.testTimeout = 20 * 1000; // 20 seconds

// Enforce an "expect" argument or expect() call in all test bodies.
QUnit.config.requireExpects = true;

/**
 * Load the TestSwarm listener if swarmURL is in the address.
 */
(function() {
	var url = window.location.search;
	url = decodeURIComponent( url.slice( url.indexOf("swarmURL=") + "swarmURL=".length ) );

	if ( !url || url.indexOf("http") !== 0 ) {
		return;
	}

	document.write("<scr" + "ipt src='http://swarm.jquery.org/js/inject.js?" + (new Date()).getTime() + "'></scr" + "ipt>");
})();

