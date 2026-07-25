// scoreboard screen — placeholder, will be implemented in next slab

export const scoreboardScreen = {
    mount(container, state, { navigate, params }) {
        container.innerHTML = '<div class="screen"><h2>scoreboard</h2><p>Coming soon...</p><button onclick="location.hash=\'\'" class="btn">Home</button></div>';
    },
    unmount() {},
};
