const events = [
  {
    id: "edu-pesisir",
    title: "Beasiswa Anak Pesisir",
    location: "Kupang, NTT",
    target: 85000000,
    raised: 53750000,
    image: "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=900&q=80",
    summary: "Membantu perlengkapan sekolah, biaya transport, dan kelas tambahan untuk anak pesisir."
  },
  {
    id: "pangan-keluarga",
    title: "Paket Pangan Keluarga Rentan",
    location: "Bekasi, Jawa Barat",
    target: 60000000,
    raised: 36250000,
    image: "https://images.unsplash.com/photo-1593113598332-cd288d649433?auto=format&fit=crop&w=900&q=80",
    summary: "Distribusi bahan pokok bulanan untuk keluarga terdampak krisis pendapatan."
  },
  {
    id: "klinik-keliling",
    title: "Klinik Keliling Desa Terpencil",
    location: "Sigi, Sulawesi Tengah",
    target: 120000000,
    raised: 78400000,
    image: "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=900&q=80",
    summary: "Layanan pemeriksaan dasar, obat esensial, dan edukasi kesehatan ibu-anak."
  },
  {
    id: "rumah-layak",
    title: "Perbaikan Rumah Layak Huni",
    location: "Lombok Timur, NTB",
    target: 95000000,
    raised: 42100000,
    image: "https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=900&q=80",
    summary: "Renovasi atap, sanitasi, dan akses air bersih untuk hunian keluarga pra-sejahtera."
  }
];

const rupiah = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0
});

const state = {
  mode: "login",
  users: JSON.parse(localStorage.getItem("equafundUsers") || "[]"),
  currentUser: JSON.parse(localStorage.getItem("equafundSession") || "null"),
  transactions: JSON.parse(localStorage.getItem("equafundTransactions") || "[]")
};

const eventGrid = document.querySelector("#eventGrid");
const eventSelect = document.querySelector("#eventSelect");
const totalRaised = document.querySelector("#totalRaised");
const transactionList = document.querySelector("#transactionList");
const donationForm = document.querySelector("#donationForm");
const donationMessage = document.querySelector("#donationMessage");
const authDialog = document.querySelector("#authDialog");
const authForm = document.querySelector("#authForm");
const authActions = document.querySelector("#authActions");
const authTitle = document.querySelector("#authTitle");
const authEyebrow = document.querySelector("#authEyebrow");
const authSubmit = document.querySelector("#authSubmit");
const authMessage = document.querySelector("#authMessage");
const nameField = document.querySelector("#nameField");
const authName = document.querySelector("#authName");
const authEmail = document.querySelector("#authEmail");
const authPassword = document.querySelector("#authPassword");
const donorName = document.querySelector("#donorName");

function save() {
  localStorage.setItem("equafundUsers", JSON.stringify(state.users));
  localStorage.setItem("equafundSession", JSON.stringify(state.currentUser));
  localStorage.setItem("equafundTransactions", JSON.stringify(state.transactions));
}

function getEvent(id) {
  return events.find((event) => event.id === id);
}

function calculateRaised(event) {
  const extra = state.transactions
    .filter((transaction) => transaction.eventId === event.id)
    .reduce((sum, transaction) => sum + transaction.amount, 0);
  return event.raised + extra;
}

function renderEvents() {
  eventGrid.innerHTML = events
    .map((event) => {
      const raised = calculateRaised(event);
      const percent = Math.min(Math.round((raised / event.target) * 100), 100);

      return `
        <article class="event-card">
          <img src="${event.image}" alt="${event.title}" />
          <div class="event-body">
            <div class="event-meta">${event.location}</div>
            <h3>${event.title}</h3>
            <p>${event.summary}</p>
            <div class="progress" aria-label="Progress ${percent}%">
              <span style="width: ${percent}%"></span>
            </div>
            <div class="event-meta">
              <strong>${rupiah.format(raised)}</strong>
              <span>dari ${rupiah.format(event.target)}</span>
            </div>
            <button class="ghost-button" type="button" data-pick-event="${event.id}">Donasi ke Event</button>
          </div>
        </article>
      `;
    })
    .join("");

  eventSelect.innerHTML = events
    .map((event) => `<option value="${event.id}">${event.title}</option>`)
    .join("");

  const total = events.reduce((sum, event) => sum + calculateRaised(event), 0);
  totalRaised.textContent = rupiah.format(total);
}

function renderAuth() {
  if (state.currentUser) {
    authActions.innerHTML = `
      <span class="event-meta">Halo, ${state.currentUser.name}</span>
      <button class="ghost-button" type="button" id="logoutButton">Keluar</button>
    `;
    donorName.value = state.currentUser.name;
    donationMessage.textContent = "Transaksi akan tercatat atas akun yang sedang login.";
    document.querySelector("#logoutButton").addEventListener("click", () => {
      state.currentUser = null;
      save();
      renderAuth();
      renderTransactions();
    });
    return;
  }

  authActions.innerHTML = `
    <button class="ghost-button" type="button" data-open-auth="login">Masuk</button>
    <button class="primary-button" type="button" data-open-auth="register">Daftar</button>
  `;
  donationMessage.textContent = "Login dulu agar transaksi tercatat atas akunmu.";
}

function renderTransactions() {
  const items = state.currentUser
    ? state.transactions.filter((transaction) => transaction.email === state.currentUser.email)
    : state.transactions.slice(-4);

  if (!items.length) {
    transactionList.innerHTML = `
      <div class="empty-state">
        Belum ada transaksi. Pilih event bantuan lalu buat transaksi donasi pertama.
      </div>
    `;
    return;
  }

  transactionList.innerHTML = items
    .slice()
    .reverse()
    .map((transaction) => {
      const event = getEvent(transaction.eventId);
      return `
        <article class="transaction-card">
          <div>
            <strong>${event?.title || "Event Bantuan"}</strong>
            <div class="transaction-meta">
              <span>${transaction.donor}</span>
              <span>${transaction.method}</span>
              <span>${transaction.date}</span>
            </div>
          </div>
          <div class="transaction-amount">${rupiah.format(transaction.amount)}</div>
        </article>
      `;
    })
    .join("");
}

function setAuthMode(mode) {
  state.mode = mode;
  const isRegister = mode === "register";
  authEyebrow.textContent = isRegister ? "Registrasi" : "Login";
  authTitle.textContent = isRegister ? "Buat akun EquaFund" : "Masuk ke EquaFund";
  authSubmit.textContent = isRegister ? "Daftar" : "Masuk";
  nameField.style.display = isRegister ? "grid" : "none";
  authName.required = isRegister;
  authMessage.textContent = "";
  authForm.reset();
  authDialog.showModal();
}

document.addEventListener("click", (event) => {
  const authButton = event.target.closest("[data-open-auth]");
  const pickButton = event.target.closest("[data-pick-event]");

  if (authButton) {
    setAuthMode(authButton.dataset.openAuth);
  }

  if (pickButton) {
    eventSelect.value = pickButton.dataset.pickEvent;
    document.querySelector("#donate").scrollIntoView({ behavior: "smooth" });
  }
});

document.querySelector("#closeAuth").addEventListener("click", () => authDialog.close());

authForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const email = authEmail.value.trim().toLowerCase();
  const password = authPassword.value;

  if (password.length < 6) {
    authMessage.textContent = "Password minimal 6 karakter.";
    return;
  }

  if (state.mode === "register") {
    if (state.users.some((user) => user.email === email)) {
      authMessage.textContent = "Email sudah terdaftar. Silakan login.";
      return;
    }

    const user = { name: authName.value.trim(), email, password };
    state.users.push(user);
    state.currentUser = { name: user.name, email: user.email };
  } else {
    const user = state.users.find((item) => item.email === email && item.password === password);
    if (!user) {
      authMessage.textContent = "Email atau password belum cocok.";
      return;
    }
    state.currentUser = { name: user.name, email: user.email };
  }

  save();
  authDialog.close();
  renderAuth();
  renderTransactions();
});

donationForm.addEventListener("submit", (event) => {
  event.preventDefault();

  if (!state.currentUser) {
    setAuthMode("login");
    authMessage.textContent = "Login atau registrasi dulu sebelum membuat transaksi.";
    return;
  }

  const amount = Number(document.querySelector("#donationAmount").value);
  const transaction = {
    id: crypto.randomUUID(),
    donor: donorName.value.trim() || state.currentUser.name,
    email: state.currentUser.email,
    eventId: eventSelect.value,
    amount,
    method: document.querySelector("#paymentMethod").value,
    date: new Date().toLocaleString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  };

  state.transactions.push(transaction);
  save();
  donationForm.reset();
  donorName.value = state.currentUser.name;
  document.querySelector("#donationAmount").value = 50000;
  donationMessage.textContent = `Transaksi berhasil dibuat: ${rupiah.format(amount)}.`;
  renderEvents();
  renderTransactions();
  document.querySelector("#transactions").scrollIntoView({ behavior: "smooth" });
});

renderEvents();
renderAuth();
renderTransactions();
