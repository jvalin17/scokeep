// Scokeep — client-side router and state manager
// Screens will be added in frontend slabs

const state = {
    playground: null,
    game: null,
    currentEntry: null,
};

function renderApp() {
    const appElement = document.getElementById("app");
    appElement.innerHTML = `
        <h1>Scokeep</h1>
        <p>Score tracker for Kachuful</p>
    `;
}

window.addEventListener("hashchange", renderApp);
renderApp();
