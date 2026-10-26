# VeriSight frontend redesign (hybrid style)

This is a visual redesign of the existing React frontend. The existing routes and API calls are preserved:
- `/` login
- `/signup` signup
- `/home` overview dashboard
- `/scan` text/image/video scan and results
- `/history` saved scan history

## Run locally

1. Extract this folder.
2. Open a terminal in the `Frontend` folder.
3. Run `npm install` to install dependencies for your operating system.
4. Run `npm run dev`.
5. Start your existing Flask backend separately on `http://127.0.0.1:5000`.

The frontend's API base URL is still configured in `src/api.js`. Change it only if your Flask backend uses a different host/port.

## Design changes

- Dark navy sidebar and premium hybrid SaaS dashboard
- Light content panels with restrained blue/violet accents
- Responsive detector cards, scan workspace, result report and history
- Redesigned login/signup experience
- Dark/light theme toggle retained
- Existing authentication, scan and history API calls retained

## Tavily / reasoning note

The backend currently returns an explanation and `sources_checked` count, not individual source URLs. The redesigned frontend displays the explanation and the count it receives. To render clickable Tavily source cards, the backend response must also include a `sources` array (title, URL, and optionally a short snippet).
