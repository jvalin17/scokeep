// roundend screen — placeholder, will be implemented in next slab

export const roundendScreen = {
    mount(container, state, { navigate, params }) {
        container.innerHTML = '<div class="screen"><h2>roundend</h2><p>Coming soon...</p><button onclick="location.hash=\'\'" class="btn">Home</button></div>';
    },
    unmount() {},
};
