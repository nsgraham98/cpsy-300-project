// js/auth.js (Firebase Auth via CDN ESM)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
import { firebaseConfig } from "./firebase-config.js";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

function setError(msg) {
  const el = document.getElementById("authError");
  if (!el) return;
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.textContent = msg;
}

function showAppForUser(user) {
  document.getElementById("authGate")?.classList.add("hidden");
  document.getElementById("dashboardApp")?.classList.remove("hidden");

  const userBox = document.getElementById("userBox");
  const userName = document.getElementById("userName");
  if (userBox) userBox.classList.remove("hidden");
  if (userName) {
    userName.textContent = user.displayName || user.email || "User";
  }
}

function showAuthGate() {
  document.getElementById("dashboardApp")?.classList.add("hidden");
  document.getElementById("authGate")?.classList.remove("hidden");
  document.getElementById("userBox")?.classList.add("hidden");
}

export function initAuth({ onLoggedIn } = {}) {
  const gbtn = document.getElementById("loginGoogleBtn");
  // Wire buttons
  document
    .getElementById("loginEmailBtn")
    ?.addEventListener("click", async () => {
      setError("");
      const email = document.getElementById("email")?.value?.trim();
      const password = document.getElementById("password")?.value;

      if (!email || !password) return setError("Email and password required.");

      try {
        await signInWithEmailAndPassword(auth, email, password);
      } catch (e) {
        setError(e?.message || "Login failed.");
      }
    });

  document
    .getElementById("registerEmailBtn")
    ?.addEventListener("click", async () => {
      setError("");
      const email = document.getElementById("email")?.value?.trim();
      const password = document.getElementById("password")?.value;

      if (!email || !password) return setError("Email and password required.");

      try {
        const cred = await createUserWithEmailAndPassword(
          auth,
          email,
          password
        );

        // Optional: set a displayName from email prefix
        const name = email.split("@")[0];
        await updateProfile(cred.user, { displayName: name });
      } catch (e) {
        setError(e?.message || "Registration failed.");
      }
    });

  document
    .getElementById("loginGoogleBtn")
    ?.addEventListener("click", async () => {
      setError("");
      try {
        await signInWithPopup(auth, googleProvider);
      } catch (e) {
        setError(e?.message || "Google login failed.");
      }
    });

  document.getElementById("logoutBtn")?.addEventListener("click", async () => {
    await signOut(auth);
  });

  // Gate the UI
  onAuthStateChanged(auth, (user) => {
    if (user) {
      showAppForUser(user);
      onLoggedIn?.(user);
    } else {
      showAuthGate();
    }
  });
}

export function getCurrentUser() {
  return auth.currentUser;
}
