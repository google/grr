CREATE DATABASE grr;

CREATE
  USER grr IDENTIFIED BY "grr";

GRANT ALL PRIVILEGES ON grr.* TO 'grr' @'%';

CREATE DATABASE fleetspeak;

CREATE
  USER fleetspeak IDENTIFIED BY "fleetspeak";

GRANT ALL PRIVILEGES ON fleetspeak.* TO 'fleetspeak' @'%';
GRANT SUPER ON *.* TO 'grr' @'%';

CREATE
  USER grrdev IDENTIFIED BY "grrdev";

GRANT ALL PRIVILEGES ON *.* TO 'grrdev' @'%';
