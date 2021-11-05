PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS features;
DROP TABLE IF EXISTS languages;
DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS server_features;

CREATE TABLE features(
	/* Short name for URLs and email submissions */
	name PRIMARY KEY,

	/* One-line description of the feature to display on server page */
	description UNIQUE
);

CREATE TABLE languages(
	/* Short name for URLs and email submissions */
	name PRIMARY KEY,

	/* Pretty name. If it's NULL, capitalized `name` is used instead */
	screen_name
);

CREATE TABLE servers(
	/* Short name for URLs and email submissions */
	name PRIMARY KEY,

	/* Official name. If it's NULL, `name` is used instead */
	screen_name,

	/* ASCII-art logo */
	logo,

	/* Multi-line Gemtext description to display on server page */
	description,

	/* Homepage URL */
	homepage,

	/* Full Repology URL, e.g. "https://repology.org/project/foobar" */
	repology,

	/* The main language used to write this server */
	lang,
	FOREIGN KEY(lang)
		REFERENCES languages(name)
		ON DELETE RESTRICT
);

CREATE TABLE server_features(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	server_name NOT NULL,
	feature_name NOT NULL,
	FOREIGN KEY(server_name)
		REFERENCES servers(name)
		ON DELETE CASCADE,
	FOREIGN KEY(feature_name)
		REFERENCES features(name)
		ON DELETE CASCADE
);

INSERT INTO features(name, description)
VALUES
	("gencert",	"Automatic TLS certificate generation"),
	("vhost",	"Virtual Host support"),
	("userdirs",	"Public User Directories support"),
	("cgi",		"CGI support"),
	("scgi",	"SCGI support"),
	("fastcgi",	"FastCGI support");

INSERT INTO languages(name, screen_name)
VALUES
	("c",		NULL),
	("clojure",	NULL),
	("common_lisp",	"Common Lisp"),
	("cpp",		"C++"),
	("cs",		"C#"),
	("d",		NULL),
	("erlang",	NULL),
	("go",		NULL),
	("haskell",	NULL),
	("java",	NULL),
	("kotlin",	NULL),
	("lua",		NULL),
	("nim",		NULL),
	("node",	"Node.js"),
	("php",		"PHP"),
	("perl",	NULL),
	("prolog",	NULL),
	("python",	NULL),
	("racket",	NULL),
	("ruby",	NULL),
	("rust",	NULL),
	("scala",	NULL),
	("scheme",	NULL),
	("shell",	NULL),
	("typescript",	"TypeScript");
