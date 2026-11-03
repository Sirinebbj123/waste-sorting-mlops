// EcoTri : envoie une image à POST /predict et affiche les déchets, leur matière et leur poubelle.

const ICONES = { cardboard: "📦", glass: "🍾", metal: "🥫", paper: "📄", plastic: "🧴", trash: "🗑️" };
const NOMS_BACS = { jaune: "Bac jaune", verte: "Bac vert", grise: "Bac gris" };
const CLE_HISTORIQUE = "ecotri-historique";
const CLE_THEME = "ecotri-theme";
const TAILLE_HISTORIQUE = 12;

const $ = (id) => document.getElementById(id);
const etat = { image: null, resultat: null, flux: null, enCours: false };

// ---------- Utilitaires ----------

function couleur(bac) {
  return getComputedStyle(document.documentElement).getPropertyValue("--" + bac).trim() || "#16a34a";
}

function lireStockage(cle, defaut) {
  try {
    return JSON.parse(localStorage.getItem(cle)) ?? defaut;
  } catch {
    return defaut; // navigation privée ou stockage bloqué : la page marche quand même
  }
}

function ecrireStockage(cle, valeur) {
  try {
    localStorage.setItem(cle, JSON.stringify(valeur));
  } catch {
    /* stockage plein ou bloqué : on ignore */
  }
}

function toast(message) {
  const t = $("toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.minuteur);
  toast.minuteur = setTimeout(() => (t.hidden = true), 4000);
}

function chargerImage(source) {
  return new Promise((ok, ko) => {
    const img = new Image();
    img.onload = () => ok(img);
    img.onerror = () => ko(new Error("Image illisible"));
    img.src = source;
  });
}

// ---------- Thème clair / sombre ----------

function appliquerTheme(theme) {
  document.documentElement.dataset.theme = theme;
  if (etat.resultat) dessiner(etat.image, etat.resultat.detections); // les couleurs changent
  afficherStats();
}

$("theme").addEventListener("click", () => {
  const nouveau = document.documentElement.dataset.theme === "sombre" ? "clair" : "sombre";
  ecrireStockage(CLE_THEME, nouveau);
  appliquerTheme(nouveau);
});

// ---------- Onglets Photo / Webcam ----------

document.querySelectorAll(".onglet").forEach((onglet) => {
  onglet.addEventListener("click", () => {
    document.querySelectorAll(".onglet").forEach((o) => o.classList.toggle("actif", o === onglet));
    const webcam = onglet.dataset.mode === "webcam";
    $("panneau-photo").hidden = webcam;
    $("panneau-webcam").hidden = !webcam;
    if (!webcam) arreterCamera();
  });
});

// ---------- Photo : clic, glisser-déposer, coller ----------

$("fichier").addEventListener("change", () => {
  if ($("fichier").files[0]) analyserFichier($("fichier").files[0]);
  $("fichier").value = ""; // permet de renvoyer la même photo
});

const depot = $("depot");
["dragenter", "dragover"].forEach((evt) =>
  depot.addEventListener(evt, (e) => {
    e.preventDefault();
    depot.classList.add("survol");
  })
);
["dragleave", "drop"].forEach((evt) => depot.addEventListener(evt, () => depot.classList.remove("survol")));
depot.addEventListener("drop", (e) => {
  e.preventDefault();
  const fichier = e.dataTransfer.files[0];
  if (fichier) analyserFichier(fichier);
});

document.addEventListener("paste", (e) => {
  const fichier = [...e.clipboardData.files].find((f) => f.type.startsWith("image/"));
  if (fichier) analyserFichier(fichier);
});

async function analyserFichier(fichier) {
  if (!fichier.type.startsWith("image/")) {
    toast("Ce fichier n'est pas une image");
    return;
  }
  const image = await chargerImage(URL.createObjectURL(fichier));
  await analyser(fichier, image, true);
}

// ---------- Webcam ----------

$("camera").addEventListener("click", async () => {
  if (etat.flux) {
    arreterCamera();
    return;
  }
  try {
    etat.flux = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 } },
    });
  } catch {
    toast("Caméra inaccessible : autorise-la dans le navigateur");
    return;
  }
  $("video").srcObject = etat.flux;
  $("video-vide").hidden = true;
  $("camera").textContent = "Éteindre la caméra";
  $("capturer").disabled = false;
  $("continu").disabled = false;
});

function arreterCamera() {
  if (!etat.flux) return;
  etat.flux.getTracks().forEach((piste) => piste.stop());
  etat.flux = null;
  $("video").srcObject = null;
  $("video-vide").hidden = false;
  $("camera").textContent = "Allumer la caméra";
  $("capturer").disabled = true;
  $("continu").checked = false;
  $("continu").disabled = true;
}

async function capturer(garder) {
  const video = $("video");
  if (!video.videoWidth) return;
  const toile = document.createElement("canvas");
  toile.width = video.videoWidth;
  toile.height = video.videoHeight;
  toile.getContext("2d").drawImage(video, 0, 0);
  const blob = await new Promise((ok) => toile.toBlob(ok, "image/jpeg", 0.9));
  const image = await chargerImage(toile.toDataURL("image/jpeg", 0.9));
  await analyser(blob, image, garder);
}

$("capturer").addEventListener("click", () => capturer(true));

// Analyse en continu : une image dès que la précédente est traitée, au plus une par seconde
$("continu").addEventListener("change", async () => {
  while ($("continu").checked && etat.flux) {
    const debut = Date.now();
    await capturer(false);
    await new Promise((ok) => setTimeout(ok, Math.max(0, 1000 - (Date.now() - debut))));
  }
});

// ---------- Appel de l'API ----------

async function analyser(donnees, image, garder) {
  if (etat.enCours) return;
  etat.enCours = true;
  etat.image = image;
  $("resultat").hidden = false;
  dessiner(image, []);
  $("chargement").hidden = false;

  const formulaire = new FormData();
  formulaire.append("fichier", donnees, "image.jpg");
  try {
    const reponse = await fetch("/predict", { method: "POST", body: formulaire });
    const corps = await reponse.json();
    if (!reponse.ok) throw new Error(corps.detail || "Erreur " + reponse.status);
    etat.resultat = corps;
    afficherResultat(corps);
    if (garder) ajouterHistorique(image, corps);
  } catch (e) {
    toast("Erreur : " + e.message);
  } finally {
    $("chargement").hidden = true;
    etat.enCours = false;
  }
}

// ---------- Affichage du résultat ----------

function dessiner(image, detections, surligne = -1) {
  const toile = $("dessin");
  toile.width = image.naturalWidth;
  toile.height = image.naturalHeight;
  const ctx = toile.getContext("2d");
  ctx.drawImage(image, 0, 0);
  const trait = Math.max(2, image.naturalWidth / 220);
  ctx.font = `600 ${trait * 6}px system-ui, sans-serif`;
  ctx.lineJoin = "round";

  detections.forEach((d, i) => {
    const [x1, y1, x2, y2] = d.boite;
    const c = couleur(d.poubelle);
    const actif = surligne === -1 || surligne === i;
    ctx.globalAlpha = actif ? 1 : 0.3;
    ctx.strokeStyle = c;
    ctx.lineWidth = surligne === i ? trait * 1.8 : trait;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    const texte = `${i + 1} · ${d.matiere_fr}`;
    const h = trait * 9;
    const l = ctx.measureText(texte).width + trait * 4;
    const y = y1 - h < 0 ? y1 : y1 - h;
    ctx.fillStyle = c;
    ctx.fillRect(x1 - trait / 2, y, l, h);
    ctx.fillStyle = d.poubelle === "jaune" ? "#422006" : "white";
    ctx.fillText(texte, x1 + trait * 1.5, y + h * 0.72);
  });
  ctx.globalAlpha = 1;
}

function afficherResultat(corps) {
  dessiner(etat.image, corps.detections);
  const n = corps.nb_dechets;
  $("titre-resultat").textContent = n === 1 ? "1 déchet" : `${n} déchets`;
  $("duree").textContent = `${Math.round(corps.duree_ms)} ms`;

  const remarque = $("remarque");
  remarque.hidden = corps.mode !== "image_entiere";
  remarque.textContent = "Aucun déchet isolé repéré : l'image entière a été classée.";

  // Compteurs par poubelle
  const parBac = {};
  corps.detections.forEach((d) => (parBac[d.poubelle] = (parBac[d.poubelle] || 0) + 1));
  $("compteurs").replaceChildren(
    ...Object.entries(parBac).map(([bac, nb]) => {
      const span = document.createElement("span");
      span.className = "compteur";
      span.innerHTML = `<span class="bac ${bac}" style="margin:0"></span>`;
      span.append(`${NOMS_BACS[bac]} · ${nb}`);
      return span;
    })
  );

  // Une carte par déchet
  $("liste").replaceChildren(
    ...corps.detections.map((d, i) => {
      const li = document.createElement("li");
      li.className = "dechet";
      li.style.animationDelay = `${i * 60}ms`;
      li.innerHTML = `
        <span class="dechet-icone"></span>
        <div>
          <div class="dechet-nom"></div>
          <div class="barre-confiance"><span></span></div>
          <div class="dechet-conf"></div>
        </div>
        <span class="puce ${d.poubelle}"></span>`;
      li.querySelector(".dechet-icone").textContent = ICONES[d.matiere] || "♻️";
      li.querySelector(".dechet-nom").textContent = `${i + 1}. ${d.matiere_fr}`;
      li.querySelector(".dechet-conf").textContent = `Confiance ${Math.round(d.confiance_matiere * 100)} %`;
      li.querySelector(".puce").textContent = NOMS_BACS[d.poubelle];
      requestAnimationFrame(() => (li.querySelector(".barre-confiance span").style.width = `${d.confiance_matiere * 100}%`));
      // Survoler une carte met sa boîte en avant sur la photo
      li.addEventListener("mouseenter", () => dessiner(etat.image, corps.detections, i));
      li.addEventListener("mouseleave", () => dessiner(etat.image, corps.detections));
      return li;
    })
  );
}

// ---------- Historique (gardé dans le navigateur) ----------

function vignette(image) {
  const toile = document.createElement("canvas");
  const echelle = 160 / Math.max(image.naturalWidth, image.naturalHeight);
  toile.width = Math.round(image.naturalWidth * echelle);
  toile.height = Math.round(image.naturalHeight * echelle);
  toile.getContext("2d").drawImage(image, 0, 0, toile.width, toile.height);
  return toile.toDataURL("image/jpeg", 0.7);
}

function ajouterHistorique(image, corps) {
  const historique = lireStockage(CLE_HISTORIQUE, []);
  historique.unshift({ date: Date.now(), vignette: vignette(image), resultat: corps });
  ecrireStockage(CLE_HISTORIQUE, historique.slice(0, TAILLE_HISTORIQUE));
  afficherHistorique();
  afficherStats();
}

function afficherHistorique() {
  const historique = lireStockage(CLE_HISTORIQUE, []);
  $("historique-vide").hidden = historique.length > 0;
  $("historique").replaceChildren(
    ...historique.map((entree) => {
      const bouton = document.createElement("button");
      bouton.className = "vignette";
      bouton.type = "button";
      bouton.title = new Date(entree.date).toLocaleString("fr-FR");
      bouton.innerHTML = `<img alt=""><span></span>`;
      bouton.querySelector("img").src = entree.vignette;
      bouton.querySelector("span").textContent = entree.resultat.nb_dechets;
      bouton.addEventListener("click", () => revoir(entree));
      return bouton;
    })
  );
}

async function revoir(entree) {
  // La vignette est petite : on remet les boîtes à son échelle
  const image = await chargerImage(entree.vignette);
  const e = image.naturalWidth / entree.resultat.largeur;
  const detections = entree.resultat.detections.map((d) => ({ ...d, boite: d.boite.map((v) => v * e) }));
  etat.image = image;
  etat.resultat = { ...entree.resultat, detections };
  $("resultat").hidden = false;
  afficherResultat(etat.resultat);
  $("resultat").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("vider").addEventListener("click", () => {
  ecrireStockage(CLE_HISTORIQUE, []);
  afficherHistorique();
  afficherStats();
});

// ---------- Statistiques ----------

function afficherStats() {
  const parBac = { jaune: 0, verte: 0, grise: 0 };
  lireStockage(CLE_HISTORIQUE, []).forEach((entree) =>
    entree.resultat.detections.forEach((d) => (parBac[d.poubelle] += 1))
  );
  const total = parBac.jaune + parBac.verte + parBac.grise;
  const anneau = $("anneau");
  anneau.classList.toggle("vide-stat", total === 0);
  anneau.style.setProperty("--j", total ? (parBac.jaune / total) * 100 : 0);
  anneau.style.setProperty("--v", total ? (parBac.verte / total) * 100 : 0);
  $("total-dechets").textContent = total;
  $("legende").replaceChildren(
    ...Object.entries(parBac).map(([bac, nb]) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="bac ${bac}" style="margin:0"></span>`;
      li.append(`${NOMS_BACS[bac]} : ${nb}`);
      return li;
    })
  );
}

// ---------- Informations sur les modèles ----------

async function chargerInfos() {
  try {
    const reponse = await fetch("/info");
    if (!reponse.ok) throw new Error();
    const info = await reponse.json();
    const cls = info.scores.classifieur || {};
    const det = info.scores.detecteur || {};
    const pourcent = (v) => (v === undefined ? "?" : `${Math.round(v * 100)} %`);
    $("modeles").textContent =
      `Détecteur ${info.versions.detecteur} · mAP50 ${pourcent(det.val_mAP50)}  —  ` +
      `Classifieur ${info.versions.classifieur} · F1 ${pourcent(cls.val_f1_macro)}`;
  } catch {
    $("modeles").textContent = "Modèles indisponibles : l'API répond-elle ?";
  }
}

// ---------- Démarrage ----------

const themePrefere = window.matchMedia("(prefers-color-scheme: dark)").matches ? "sombre" : "clair";
appliquerTheme(lireStockage(CLE_THEME, themePrefere));
afficherHistorique();
afficherStats();
chargerInfos();