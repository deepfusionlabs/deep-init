// Seed data — contains planted PII for redaction testing (all fictional)
export const users = [
  { id: 1, full_name: "Dana Cohen", email: "dana.cohen@gmail.com", phone: "+972-54-1234567",
    teudat_zehut: "203458179", date_of_birth: "1990-03-14", salary: 28500, status: "active" },
  { id: 2, full_name: "Yossi Levi", email: "yossi@example.co.il", phone: "+972-52-7654321",
    teudat_zehut: "318273645", date_of_birth: "1985-11-02", salary: 41200, status: "inactive" },
];
export const orderCount = 1842;          // not PII — must be kept
