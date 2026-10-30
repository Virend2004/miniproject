/* ==========================================================================
   GL BAJAJ - Login & Registration Controller with Image Options
   File: login.js
   Features:
   - Dynamic Profile Image / Avatar Selection on Login & Register
   - Photo Upload from Local Device (JPG, PNG, WebP)
   - Real-time User Detection & Profile Image Display on Username Entry
   - Institutional Preset Avatars (Student, Faculty, Staff, Tech)
   - Campus Photo Background Toggle
   - Dual-mode sync with SQLite REST backend & persistent LocalStorage
   ========================================================================== */

let currentLoginAvatar = "";
let currentRegAvatar = "";
let customRegImageUploaded = false;
let activeModalTarget = "login"; // 'login' or 'reg'
let modalSelectedAvatar = "";
let usernameLookupTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("loginContainer");
    const registerBtn = document.querySelector(".register-btn");
    const loginBtn = document.querySelector(".login-btn");

    // Initialize Default Avatars
    if (typeof CollegeDB !== "undefined" && CollegeDB.DEFAULT_AVATARS) {
        currentLoginAvatar = CollegeDB.DEFAULT_AVATARS.student;
        currentRegAvatar = CollegeDB.DEFAULT_AVATARS.student;
        modalSelectedAvatar = CollegeDB.DEFAULT_AVATARS.student;

        // Set preset preview images in modal
        for (const [key, val] of Object.entries(CollegeDB.DEFAULT_AVATARS)) {
            const el = document.getElementById(`presetImg_${key}`);
            if (el) el.src = val;
        }

        const loginImg = document.getElementById("loginAvatarPreview");
        if (loginImg) loginImg.src = currentLoginAvatar;

        const regImg = document.getElementById("regAvatarPreview");
        if (regImg) regImg.src = currentRegAvatar;
    }

    // Restore saved campus background preference
    if (localStorage.getItem("GLB_CAMPUS_BG") === "true") {
        document.body.classList.add("campus-bg");
        const btn = document.getElementById("bgToggleBtn");
        if (btn) btn.innerHTML = `<i class="bx bx-sun"></i> Minimal Theme`;
    }

    // Toggle Panels
    if (registerBtn) {
        registerBtn.addEventListener("click", () => {
            clearAlerts();
            container.classList.add("active");
            history.replaceState(null, "", "#signup");
        });
    }

    if (loginBtn) {
        loginBtn.addEventListener("click", () => {
            clearAlerts();
            container.classList.remove("active");
            history.replaceState(null, "", "#login");
        });
    }

    // Auto-open Register if coming from Sign Up button
    if (window.location.hash === "#signup" || window.location.search.includes("mode=register")) {
        container.classList.add("active");
    }

    // Check if there was a previous user session to welcome them with their photo
    if (typeof CollegeDB !== "undefined") {
        const lastSession = CollegeDB.getCurrentSession();
        if (lastSession && lastSession.username) {
            applyUserToLoginPreview({
                fullname: lastSession.fullname,
                role: lastSession.role,
                avatar: lastSession.avatar || CollegeDB.DEFAULT_AVATARS[lastSession.role] || CollegeDB.DEFAULT_AVATARS.student
            });
            const userField = document.getElementById("loginUsername");
            if (userField && !userField.value) {
                userField.value = lastSession.username;
            }
            const roleSelect = document.getElementById("loginRole");
            if (roleSelect && lastSession.role) {
                roleSelect.value = lastSession.role;
            }
        }
    }

    // ==========================================
    // Registration Form Submission
    // ==========================================
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlerts();

            const role = document.getElementById("regRole").value;
            const fullname = document.getElementById("regFullname").value.trim();
            const idNumber = document.getElementById("regIdNumber").value.trim();
            const username = document.getElementById("regUsername").value.trim();
            const email = document.getElementById("regEmail").value.trim();
            const password = document.getElementById("regPassword").value;

            if (!role) {
                showAlert("registerAlert", "Please select your role (Student, Faculty, Staff, etc.).", "error");
                return;
            }

            if (password.length < 4) {
                showAlert("registerAlert", "Password must be at least 4 characters long.", "error");
                return;
            }

            const submitBtn = document.getElementById("regSubmitBtn");
            submitBtn.disabled = true;
            submitBtn.textContent = "Creating Account...";

            try {
                const res = await CollegeDB.register({
                    fullname,
                    role,
                    idNumber,
                    username,
                    email,
                    password,
                    avatar: currentRegAvatar
                });

                showAlert("registerAlert", `Registered successfully as ${role.toUpperCase()}! Switching to login...`, "success");

                // Pre-fill login form with new user & their photo
                document.getElementById("loginRole").value = role;
                document.getElementById("loginUsername").value = username;
                document.getElementById("loginPassword").value = password;

                applyUserToLoginPreview({
                    fullname: fullname || username,
                    role: role,
                    avatar: currentRegAvatar
                });

                registerForm.reset();
                customRegImageUploaded = false;

                // Switch back to login panel
                setTimeout(() => {
                    container.classList.remove("active");
                    showAlert("loginAlert", `Account ready! Click Login to enter your portal.`, "success");
                }, 1300);

            } catch (err) {
                showAlert("registerAlert", err.message || "Registration failed. Please try again.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = "Register";
            }
        });
    }

    // ==========================================
    // Login Form Submission
    // ==========================================
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            clearAlerts();

            const role = document.getElementById("loginRole").value;
            const username = document.getElementById("loginUsername").value.trim();
            const password = document.getElementById("loginPassword").value;

            const submitBtn = document.getElementById("loginSubmitBtn");
            submitBtn.disabled = true;
            submitBtn.textContent = "Verifying Credentials...";

            try {
                const res = await CollegeDB.login(username, password, role);

                showAlert("loginAlert", `Welcome back, ${res.user.fullname}! Entering portal...`, "success");

                // Update photo if modified during login session
                if (currentLoginAvatar && currentLoginAvatar !== res.user.avatar) {
                    await CollegeDB.updateAvatar(res.user.username, currentLoginAvatar);
                }

                // Redirect to admin console if admin, or portal home
                setTimeout(() => {
                    if (res.user && (res.user.role === "staff" || res.user.role === "admin")) {
                        window.location.href = "admin.html";
                    } else {
                        window.location.href = "index.html";
                    }
                }, 900);

            } catch (err) {
                showAlert("loginAlert", err.message || "Invalid username or password.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = "Login";
            }
        });
    }
});

// ==========================================================================
// Live Username Photo & Identity Auto-Detection
// ==========================================================================
function onUsernameInput() {
    clearTimeout(usernameLookupTimer);
    const userVal = document.getElementById("loginUsername").value.trim();

    if (!userVal || userVal.length < 2) {
        // Reset to default role avatar
        const role = document.getElementById("loginRole").value;
        const defaultAv = (CollegeDB.DEFAULT_AVATARS && CollegeDB.DEFAULT_AVATARS[role]) || CollegeDB.DEFAULT_AVATARS.student;
        applyUserToLoginPreview({
            fullname: "Welcome Back",
            role: `${role} Portal`,
            avatar: defaultAv
        });
        return;
    }

    usernameLookupTimer = setTimeout(async () => {
        try {
            const res = await CollegeDB.lookupUser(userVal);
            if (res && res.found && res.user) {
                applyUserToLoginPreview({
                    fullname: res.user.fullname,
                    role: res.user.role,
                    avatar: res.user.avatar || CollegeDB.DEFAULT_AVATARS[res.user.role]
                });
                // Auto-sync role selector
                const roleSelect = document.getElementById("loginRole");
                if (roleSelect && res.user.role) {
                    roleSelect.value = res.user.role;
                }
            }
        } catch (e) {}
    }, 250);
}

function applyUserToLoginPreview(user) {
    const imgEl = document.getElementById("loginAvatarPreview");
    const nameEl = document.getElementById("loginAvatarName");
    const badgeEl = document.getElementById("loginAvatarRoleBadge");

    if (imgEl && user.avatar) {
        imgEl.src = user.avatar;
        currentLoginAvatar = user.avatar;
    }
    if (nameEl && user.fullname) {
        nameEl.textContent = user.fullname;
    }
    if (badgeEl && user.role) {
        badgeEl.textContent = `${user.role.toUpperCase()} PORTAL`;
    }
}

// When role changes on login form
function onLoginRoleChange() {
    const role = document.getElementById("loginRole").value;
    const defaultAv = (CollegeDB.DEFAULT_AVATARS && CollegeDB.DEFAULT_AVATARS[role]) || CollegeDB.DEFAULT_AVATARS.student;
    const userField = document.getElementById("loginUsername");

    if (!userField.value.trim()) {
        applyUserToLoginPreview({
            fullname: "Welcome Back",
            role: `${role} Portal`,
            avatar: defaultAv
        });
    }
}

// When role changes on register form
function onRoleChange() {
    const role = document.getElementById("regRole").value;
    const idInput = document.getElementById("regIdNumber");
    if (idInput) {
        if (role === "student") {
            idInput.placeholder = "University Roll No / Student ID";
        } else if (role === "faculty") {
            idInput.placeholder = "Faculty Employee ID (e.g. GLB-FAC-100)";
        } else if (role === "staff") {
            idInput.placeholder = "Staff ID (e.g. GLB-ADM-001)";
        } else {
            idInput.placeholder = "Visitor / Organization ID";
        }
    }

    // If user hasn't uploaded a custom photo, sync preview to role avatar
    if (!customRegImageUploaded && CollegeDB.DEFAULT_AVATARS) {
        const av = CollegeDB.DEFAULT_AVATARS[role] || CollegeDB.DEFAULT_AVATARS.student;
        currentRegAvatar = av;
        const preview = document.getElementById("regAvatarPreview");
        if (preview) preview.src = av;
    }
}

// ==========================================================================
// Image Upload Handlers
// ==========================================================================
function handleLoginImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    processImageFile(file, (dataUrl) => {
        currentLoginAvatar = dataUrl;
        const img = document.getElementById("loginAvatarPreview");
        if (img) img.src = dataUrl;
        showAlert("loginAlert", "Custom profile photo loaded! It will be saved upon login.", "success");
    });
}

function handleRegImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    processImageFile(file, (dataUrl) => {
        currentRegAvatar = dataUrl;
        customRegImageUploaded = true;
        const img = document.getElementById("regAvatarPreview");
        if (img) img.src = dataUrl;

        const badge = document.getElementById("regImageStatusBadge");
        if (badge) {
            badge.textContent = "Custom Photo Selected";
            badge.style.background = "#dcfce7";
            badge.style.color = "#15803d";
        }
        showAlert("registerAlert", "Profile photo attached successfully!", "success");
    });
}

function handleModalFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    processImageFile(file, (dataUrl) => {
        modalSelectedAvatar = dataUrl;
        // Deselect presets
        document.querySelectorAll(".preset-item").forEach(el => el.classList.remove("active"));
        applySelectedImage();
    });
}

// Helper to read and optimize image file to Base64 Data URL
function processImageFile(file, callback) {
    if (!file.type.startsWith("image/")) {
        alert("Please select a valid image file (JPG, PNG, WebP).");
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const rawUrl = e.target.result;

        // Resize down using HTML5 canvas if huge to ensure smooth SQLite storage
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement("canvas");
            const maxDim = 240;
            let width = img.width;
            let height = img.height;

            if (width > height) {
                if (width > maxDim) {
                    height = Math.round((height * maxDim) / width);
                    width = maxDim;
                }
            } else {
                if (height > maxDim) {
                    width = Math.round((width * maxDim) / height);
                    height = maxDim;
                }
            }

            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, width, height);

            const compressedDataUrl = canvas.toDataURL("image/jpeg", 0.88);
            callback(compressedDataUrl);
        };
        img.src = rawUrl;
    };
    reader.readAsDataURL(file);
}

// ==========================================================================
// Image Picker Modal
// ==========================================================================
function openImageModal(target) {
    activeModalTarget = target;
    const modal = document.getElementById("imagePickerModal");
    if (modal) modal.style.display = "flex";
}

function closeImageModal() {
    const modal = document.getElementById("imagePickerModal");
    if (modal) modal.style.display = "none";
}

function selectPreset(presetKey, element) {
    if (CollegeDB.DEFAULT_AVATARS && CollegeDB.DEFAULT_AVATARS[presetKey]) {
        modalSelectedAvatar = CollegeDB.DEFAULT_AVATARS[presetKey];
        document.querySelectorAll(".preset-item").forEach(el => el.classList.remove("active"));
        if (element) element.classList.add("active");
    }
}

function applySelectedImage() {
    if (!modalSelectedAvatar) return;

    if (activeModalTarget === "login") {
        currentLoginAvatar = modalSelectedAvatar;
        const img = document.getElementById("loginAvatarPreview");
        if (img) img.src = modalSelectedAvatar;
        showAlert("loginAlert", "Selected avatar applied to login profile.", "success");
    } else {
        currentRegAvatar = modalSelectedAvatar;
        customRegImageUploaded = true;
        const img = document.getElementById("regAvatarPreview");
        if (img) img.src = modalSelectedAvatar;

        const badge = document.getElementById("regImageStatusBadge");
        if (badge) {
            badge.textContent = "Preset Avatar Selected";
            badge.style.background = "#e0f2fe";
            badge.style.color = "#0369a1";
        }
    }
    closeImageModal();
}

// Close modal when clicking outside
window.addEventListener("click", (e) => {
    const modal = document.getElementById("imagePickerModal");
    if (e.target === modal) closeImageModal();
});

// Close modal on Escape key
window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeImageModal();
});

// ==========================================================================
// Background Theme Toggle (Campus Photo vs Minimal Gradient)
// ==========================================================================
function toggleCampusBg() {
    const body = document.body;
    const isCampus = body.classList.toggle("campus-bg");
    localStorage.setItem("GLB_CAMPUS_BG", isCampus ? "true" : "false");

    const btn = document.getElementById("bgToggleBtn");
    if (btn) {
        btn.innerHTML = isCampus
            ? `<i class="bx bx-sun"></i> Minimal Theme`
            : `<i class="bx bx-image-alt"></i> Campus Background`;
    }
}

// ==========================================================================
// Quick Demo Login Accounts
// ==========================================================================
function fillDemo(type) {
    clearAlerts();
    const roleSelect = document.getElementById("loginRole");
    const userField = document.getElementById("loginUsername");
    const passField = document.getElementById("loginPassword");

    if (type === "student") {
        roleSelect.value = "student";
        userField.value = "student";
        passField.value = "student123";
        applyUserToLoginPreview({
            fullname: "Aarav Sharma",
            role: "student",
            avatar: CollegeDB.DEFAULT_AVATARS.student
        });
        showAlert("loginAlert", "Filled Student Demo: username=student, password=student123", "success");
    } else if (type === "faculty") {
        roleSelect.value = "faculty";
        userField.value = "faculty";
        passField.value = "faculty123";
        applyUserToLoginPreview({
            fullname: "Dr. Vivek Verma",
            role: "faculty",
            avatar: CollegeDB.DEFAULT_AVATARS.faculty
        });
        showAlert("loginAlert", "Filled Faculty Demo: username=faculty, password=faculty123", "success");
    } else if (type === "admin") {
        roleSelect.value = "staff";
        userField.value = "admin";
        passField.value = "admin123";
        applyUserToLoginPreview({
            fullname: "Admin Office",
            role: "staff",
            avatar: CollegeDB.DEFAULT_AVATARS.staff
        });
        showAlert("loginAlert", "Filled Admin/Staff Demo: username=admin, password=admin123", "success");
    }
}

// Alert banner helper
function showAlert(elementId, message, type) {
    const box = document.getElementById(elementId);
    if (!box) return;
    box.className = `alert-banner ${type}`;
    box.textContent = message;
    box.style.display = "block";
}

function clearAlerts() {
    const alerts = document.querySelectorAll(".alert-banner");
    alerts.forEach(el => {
        el.style.display = "none";
        el.textContent = "";
    });
}
