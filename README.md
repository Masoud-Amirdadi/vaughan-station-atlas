# Vaughan Fire Services — Station Atlas

An interactive map of Vaughan fire-service activity for 2023–2025. Explore overall, station and yearly views of incidents, response times, occupied time and estimated idle capacity, with charts and station popups.

Acknowledgement: Vaughan Fire and Rescue Service contributed the incident data used in the atlas.

## View locally

Run `python -m http.server 8000 --bind 127.0.0.1 --directory dist` from this folder, then open http://localhost:8000. Internet access is needed for the OpenStreetMap basemap.

## GitHub Pages

Upload the contents of the supplied GitHub ZIP to a repository. Under **Settings → Pages**, choose **GitHub Actions**. The included workflow publishes `dist/` when changes are pushed to `main`, or can be run manually.

The site includes the incident details and downloads visible in the atlas. Operating-unit counts and idle capacity are estimates, as described in its **About data** panel.

Map: © OpenStreetMap contributors. Municipal boundary: York Region. Built with Leaflet and Chart.js; their licences are included in `dist/vendor/`.
