# Modifications.md

This document outlines the modifications and decisions made while completing the VectorShift Integration Technical Assessment.

---

# Frontend

### Vite Instead of Vanilla React.js
- Replaced the default `create-react-app` setup with **Vite** 
- Adjusted the project structure to align with Vite’s configuration.
- Updated the `package.json` and `vite.config.js` to ensure compatibility with the existing setup.
- Added necessary development dependencies for Vite.

### Why I used Vite ?
- I was facing some dependency conflicts and version issues with `nodejs` `npm` and `react-scripts`
- Out of habbit and to complete the assesment quickly I switched to **Vite** 
- **Everything works the same ✌️💯👌**

---

# Backend

### Redis Server
- Used **Upstash Redis**, a managed Redis cloud service, to simplify the setup and testing process.
- Updated the Redis configuration in the backend to connect to the Upstash Redis instance via its URL and credentials.

**Reason for Using Upstash:**
- Eliminated the need to install and manage a local Redis server.
- Reduced setup complexity, allowing focus on the assessment's core tasks.

---

# Run Commands
### For Frontend use below commands instaed of `npm start` 
---
`npm i`<br> `npm run dev`
---
### For Backend, everything is same ✌️💯
