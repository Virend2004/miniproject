// Initialize AOS animation library and user session
document.addEventListener("DOMContentLoaded", function () {
    if (typeof AOS !== "undefined") {
        AOS.init({
            once: true,
            duration: 1200
        });
    }

    // Check for active login session
    updateNavForSession();
});

// Update navbar and hero greeting if logged in
function updateNavForSession() {
    if (typeof CollegeDB === "undefined") return;

    const user = CollegeDB.getCurrentSession();
    const btnContainer = document.querySelector("nav .buttons");
    const heroH1 = document.querySelector(".content h1");

    if (user && btnContainer) {
        // Icon and label by role
        let roleIcon = "🎓";
        if (user.role === "faculty") roleIcon = "👨‍🏫";
        if (user.role === "staff") roleIcon = "🛡️";

        let avatarHtml = `<span style="font-size:1.1rem;">${roleIcon}</span>`;
        if (user.avatar) {
            avatarHtml = `<img src="${user.avatar}" alt="Avatar" style="width:28px; height:28px; border-radius:50%; object-fit:cover; border:1.5px solid #38bdf8; background:#fff;">`;
        }

        btnContainer.innerHTML = `
            <div class="user-badge" style="display:flex; align-items:center; gap:8px; background:rgba(7,113,219,0.25); border:1px solid rgb(7,113,219); padding:4px 12px; border-radius:20px; font-size:0.9rem; color:#fff;">
                ${avatarHtml}
                <strong>${user.fullname.split(" ")[0]}</strong>
                <span style="font-size:0.75rem; background:rgb(7,113,219); padding:2px 6px; border-radius:10px; text-transform:uppercase;">${user.role}</span>
            </div>
            <div class="btn">
                <button type="button" onclick="openAdmin()" style="background:#7c3aed; border-color:#7c3aed;">Admin</button>
            </div>
            <div class="btn">
                <button type="button" onclick="logoutUser()" style="background:#ef4444; border-color:#ef4444;">Logout</button>
            </div>
            <div class="btn">
                <button type="button" onclick="openEvents()">Event</button>
            </div>
        `;

        if (heroH1) {
            heroH1.innerHTML = `Welcome, <span>${user.fullname}</span>!`;
        }
    }
}

function logoutUser() {
    if (typeof CollegeDB !== "undefined") {
        CollegeDB.logout();
    }
    alert("You have been logged out successfully.");
    window.location.reload();
}

function login() {
    window.location.href = "login.html";
}

function signUp() {
    window.location.href = "login.html#signup";
}

function neviagate() {
    window.location.href = "vivek.html";
}

function openEvents() {
    window.location.href = "events.html";
}

function openAdmin() {
    window.location.href = "admin.html";
}

// Backward-compatible alias for the event button
function event() {
    openEvents();
}
